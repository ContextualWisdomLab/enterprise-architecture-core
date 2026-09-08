"""Purpose-bound command port for verifying a completed EA target state."""

from __future__ import annotations

import json
import subprocess
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import cast
from urllib.parse import urlparse
from uuid import UUID

from ..decision_plane_http import (
    CommandRunner,
    PlannerExecutionError,
    PlannerRequestError,
    _parse_timestamp,
    _parse_uuid7,
    _postgres_environment,
    build_keyverse_authorization_config,
)
from ..identity_authorization.authorization import (
    AuthorizationContext,
    KeyverseAuthorizationConfig,
)

_TARGET_STATE_COMMAND_PATH_PREFIX = "/v1/architecture-transformations/"
_TARGET_STATE_VERIFICATION_PATH_SUFFIX = "/verification"
_VERIFY_ACTOR_ENV = "EA_VERIFY_ACTOR_REF"
_VERIFY_REASON_ENV = "EA_VERIFY_REASON_TEXT"
_ALLOWED_VERIFICATION_OUTCOMES = frozenset({"verified", "gap_detected"})
_TARGET_STATE_VERIFICATION_SQL = """
SELECT row_to_json(verification_receipt)::text
FROM (
    SELECT
        verified.transformation_history_record_id,
        verified.architecture_transformation_id,
        verified.verification_outcome_code,
        verified.outbox_event_id,
        verified.decision_request_id,
        verified.verification_recorded_at,
        verified.verification_replayed AS replayed,
        verified.next_action
    FROM architecture_core.record_target_state_verification(
        :'tenant_record_id'::uuid,
        :'architecture_transformation_id'::uuid,
        :'decision_request_id'::uuid,
        :'effective_at'::timestamptz,
        :'decision_actor_ref'::text,
        :'decision_reason_text'::text,
        :'evidence_record_id'::uuid,
        :'verification_outcome_code'::text
    ) AS verified
) AS verification_receipt;
""".strip()


@dataclass(frozen=True, slots=True)
class TargetStateVerificationRequest:
    """One immutable human decision about achieved target-state evidence."""

    architecture_transformation_id: UUID
    decision_request_id: UUID
    effective_at: datetime
    decision_reason_text: str
    evidence_record_id: UUID
    verification_outcome_code: str

    @classmethod
    def from_values(
        cls,
        architecture_transformation_id: str,
        decision_request_id: str,
        effective_at: str,
        decision_reason_text: str,
        evidence_record_id: str,
        verification_outcome_code: str,
    ) -> TargetStateVerificationRequest:
        """Validate canonical verification meaning before PostgreSQL is reachable."""

        transformation_id = _parse_uuid7(
            architecture_transformation_id,
            "architecture transformation id",
        )
        request_id = _parse_uuid7(decision_request_id, "decision request id")
        evidence_id = _parse_uuid7(evidence_record_id, "evidence record id")
        effective_time = _parse_timestamp(effective_at, "effective_at")
        reason = decision_reason_text.strip()
        if not reason or len(reason) > 4096:
            raise PlannerRequestError(
                "decision_reason_text must contain between 1 and 4096 characters"
            )
        if verification_outcome_code not in _ALLOWED_VERIFICATION_OUTCOMES:
            raise PlannerRequestError(
                "verification outcome must be verified or gap_detected"
            )
        return cls(
            architecture_transformation_id=transformation_id,
            decision_request_id=request_id,
            effective_at=effective_time,
            decision_reason_text=reason,
            evidence_record_id=evidence_id,
            verification_outcome_code=verification_outcome_code,
        )


def parse_target_state_verification_request(
    path: str,
    payload: Mapping[str, object],
) -> TargetStateVerificationRequest:
    """Bind strict verification JSON to the transformation identified by the path."""

    parsed = urlparse(path)
    if parsed.query or parsed.fragment:
        raise PlannerRequestError(
            "verification path cannot contain query or fragment data"
        )
    route = parsed.path
    if (
        not route.startswith(_TARGET_STATE_COMMAND_PATH_PREFIX)
        or not route.endswith(_TARGET_STATE_VERIFICATION_PATH_SUFFIX)
    ):
        raise PlannerRequestError("target-state verification path is invalid")
    prefix_length = len(_TARGET_STATE_COMMAND_PATH_PREFIX)
    suffix_length = len(_TARGET_STATE_VERIFICATION_PATH_SUFFIX)
    transformation_id = route[prefix_length:-suffix_length]
    if not transformation_id or "/" in transformation_id:
        raise PlannerRequestError(
            "target-state verification requires one transformation UUID"
        )
    required_names = {
        "decision_request_id",
        "effective_at",
        "decision_reason_text",
        "evidence_record_id",
        "verification_outcome_code",
    }
    if set(payload) != required_names:
        raise PlannerRequestError(
            "verification body must contain only the documented fields"
        )
    if not all(isinstance(payload[name], str) for name in required_names):
        raise PlannerRequestError("verification fields must be JSON strings")
    return TargetStateVerificationRequest.from_values(
        transformation_id,
        str(payload["decision_request_id"]),
        str(payload["effective_at"]),
        str(payload["decision_reason_text"]),
        str(payload["evidence_record_id"]),
        str(payload["verification_outcome_code"]),
    )


def build_verification_authorization_config(
    environ: Mapping[str, str],
) -> KeyverseAuthorizationConfig | None:
    """Build a Keyverse profile granting only target-state verification authority."""

    verification_environment = dict(environ)
    verification_environment["EA_READ_ROLES"] = environ.get("EA_VERIFY_ROLES", "")
    return build_keyverse_authorization_config(verification_environment)


def _unavailable_verification_writer(
    context: AuthorizationContext,
    request: TargetStateVerificationRequest,
) -> Mapping[str, object]:
    """Reject verification when no safe PostgreSQL command port exists."""

    del context, request
    raise PlannerExecutionError("target-state verification database is unavailable")


def build_target_state_verification_writer(
    dsn: str | None,
    *,
    runner: CommandRunner = subprocess.run,
    base_environment: Mapping[str, str] | None = None,
):
    """Build the verification writer without granting direct application-table SQL."""

    if not dsn:
        return _unavailable_verification_writer
    connection_environment = _postgres_environment(dsn, base_environment)
    if connection_environment is None:
        return _unavailable_verification_writer

    def writer(
        context: AuthorizationContext,
        request: TargetStateVerificationRequest,
    ) -> Mapping[str, object]:
        """Execute one idempotent target-state verification decision."""

        actor_ref = f"keyverse:{context.issuer_uri}#{context.subject_id}"
        if len(actor_ref) > 2048:
            raise PlannerExecutionError("verified actor reference is too long")
        verification_environment = dict(connection_environment)
        verification_environment[_VERIFY_ACTOR_ENV] = actor_ref
        verification_environment[_VERIFY_REASON_ENV] = request.decision_reason_text
        command = [
            "psql",
            "--no-psqlrc",
            "--tuples-only",
            "--no-align",
            "--set",
            "ON_ERROR_STOP=1",
            "--set",
            f"tenant_record_id={context.tenant_record_id}",
            "--set",
            f"architecture_transformation_id={request.architecture_transformation_id}",
            "--set",
            f"decision_request_id={request.decision_request_id}",
            "--set",
            f"effective_at={request.effective_at.isoformat()}",
            "--set",
            f"evidence_record_id={request.evidence_record_id}",
            "--set",
            f"verification_outcome_code={request.verification_outcome_code}",
            "--command",
            r"\getenv decision_actor_ref EA_VERIFY_ACTOR_REF",
            "--command",
            r"\getenv decision_reason_text EA_VERIFY_REASON_TEXT",
            "--command",
            _TARGET_STATE_VERIFICATION_SQL,
        ]
        try:
            result = runner(
                command,
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
                env=verification_environment,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            raise PlannerExecutionError(
                "target-state verification database command failed"
            ) from error
        if result.returncode != 0:
            raise PlannerExecutionError(
                "target-state verification database query failed"
            )
        try:
            payload = json.loads(result.stdout.strip())
        except json.JSONDecodeError as error:
            raise PlannerExecutionError(
                "target-state verification returned invalid JSON"
            ) from error
        if not isinstance(payload, Mapping):
            raise PlannerExecutionError(
                "target-state verification returned invalid verification receipt"
            )
        try:
            _parse_uuid7(
                cast(str, payload.get("transformation_history_record_id")),
                "transformation history record id",
            )
            _parse_uuid7(
                cast(str, payload.get("outbox_event_id")),
                "outbox event id",
            )
            _parse_timestamp(
                cast(str, payload.get("verification_recorded_at")),
                "verification_recorded_at",
            )
        except PlannerRequestError as error:
            raise PlannerExecutionError(
                "target-state verification returned invalid verification receipt"
            ) from error
        expected_action = (
            "monitor_target_state"
            if request.verification_outcome_code == "verified"
            else "replan_target_state"
        )
        if (
            payload.get("architecture_transformation_id")
            != str(request.architecture_transformation_id)
            or payload.get("verification_outcome_code")
            != request.verification_outcome_code
            or payload.get("decision_request_id") != str(request.decision_request_id)
            or not isinstance(payload.get("replayed"), bool)
            or payload.get("next_action") != expected_action
        ):
            raise PlannerExecutionError(
                "target-state verification returned invalid verification receipt"
            )
        return payload

    return writer
