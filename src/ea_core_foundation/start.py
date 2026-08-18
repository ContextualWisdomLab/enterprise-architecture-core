"""Purpose-bound command port for starting a scheduled EA transformation."""

from __future__ import annotations

import json
import subprocess
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import cast
from urllib.parse import urlparse
from uuid import UUID

from .authorization import AuthorizationContext, KeyverseAuthorizationConfig
from .service import (
    CommandRunner,
    PlannerExecutionError,
    PlannerRequestError,
    _parse_timestamp,
    _parse_uuid7,
    _postgres_environment,
    build_keyverse_authorization_config,
)

_TARGET_STATE_COMMAND_PATH_PREFIX = "/v1/architecture-transformations/"
_TARGET_STATE_START_PATH_SUFFIX = "/start"
_START_ACTOR_ENV = "EA_START_ACTOR_REF"
_START_REASON_ENV = "EA_START_REASON_TEXT"
_TARGET_STATE_START_SQL = """
SELECT row_to_json(start_receipt)::text
FROM (
    SELECT
        started.transformation_history_record_id,
        started.architecture_transformation_id,
        started.transformation_state_code,
        started.outbox_event_id,
        started.decision_request_id,
        started.start_recorded_at,
        started.start_replayed AS replayed,
        started.next_action
    FROM architecture_core.start_scheduled_transformation(
        :'tenant_record_id'::uuid,
        :'architecture_transformation_id'::uuid,
        :'decision_request_id'::uuid,
        :'effective_at'::timestamptz,
        :'decision_actor_ref'::text,
        :'decision_reason_text'::text,
        :'evidence_record_id'::uuid
    ) AS started
) AS start_receipt;
""".strip()


@dataclass(frozen=True, slots=True)
class TargetStateStartRequest:
    """One immutable decision to start a governed scheduled transformation."""

    architecture_transformation_id: UUID
    decision_request_id: UUID
    effective_at: datetime
    decision_reason_text: str
    evidence_record_id: UUID

    @classmethod
    def from_values(
        cls,
        architecture_transformation_id: str,
        decision_request_id: str,
        effective_at: str,
        decision_reason_text: str,
        evidence_record_id: str,
    ) -> TargetStateStartRequest:
        """Validate canonical command meaning before PostgreSQL is reachable."""

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
        return cls(
            architecture_transformation_id=transformation_id,
            decision_request_id=request_id,
            effective_at=effective_time,
            decision_reason_text=reason,
            evidence_record_id=evidence_id,
        )


def parse_target_state_start_request(
    path: str,
    payload: Mapping[str, object],
) -> TargetStateStartRequest:
    """Bind strict JSON to the single transformation identified by the start path."""

    parsed = urlparse(path)
    if parsed.query or parsed.fragment:
        raise PlannerRequestError("start path cannot contain query or fragment data")
    route = parsed.path
    if (
        not route.startswith(_TARGET_STATE_COMMAND_PATH_PREFIX)
        or not route.endswith(_TARGET_STATE_START_PATH_SUFFIX)
    ):
        raise PlannerRequestError("target-state start path is invalid")
    prefix_length = len(_TARGET_STATE_COMMAND_PATH_PREFIX)
    suffix_length = len(_TARGET_STATE_START_PATH_SUFFIX)
    transformation_id = route[prefix_length:-suffix_length]
    if not transformation_id or "/" in transformation_id:
        raise PlannerRequestError("target-state start requires one transformation UUID")
    required_names = {
        "decision_request_id",
        "effective_at",
        "decision_reason_text",
        "evidence_record_id",
    }
    if set(payload) != required_names:
        raise PlannerRequestError("start body must contain only the documented fields")
    if not all(isinstance(payload[name], str) for name in required_names):
        raise PlannerRequestError("start fields must be JSON strings")
    return TargetStateStartRequest.from_values(
        transformation_id,
        str(payload["decision_request_id"]),
        str(payload["effective_at"]),
        str(payload["decision_reason_text"]),
        str(payload["evidence_record_id"]),
    )


def build_start_authorization_config(
    environ: Mapping[str, str],
) -> KeyverseAuthorizationConfig | None:
    """Build a Keyverse profile whose roles grant only transformation-start authority."""

    start_environment = dict(environ)
    start_environment["EA_READ_ROLES"] = environ.get("EA_START_ROLES", "")
    return build_keyverse_authorization_config(start_environment)


def _unavailable_start_writer(
    context: AuthorizationContext,
    request: TargetStateStartRequest,
) -> Mapping[str, object]:
    """Reject start commands when no safe PostgreSQL command port exists."""

    del context, request
    raise PlannerExecutionError("target-state start database is unavailable")


def build_target_state_start_writer(
    dsn: str | None,
    *,
    runner: CommandRunner = subprocess.run,
    base_environment: Mapping[str, str] | None = None,
):
    """Build the purpose-bound start writer without granting direct table mutation."""

    if not dsn:
        return _unavailable_start_writer
    connection_environment = _postgres_environment(dsn, base_environment)
    if connection_environment is None:
        return _unavailable_start_writer

    def writer(
        context: AuthorizationContext,
        request: TargetStateStartRequest,
    ) -> Mapping[str, object]:
        """Execute one idempotent transformation-start decision through PostgreSQL."""

        actor_ref = f"keyverse:{context.issuer_uri}#{context.subject_id}"
        if len(actor_ref) > 2048:
            raise PlannerExecutionError("verified actor reference is too long")
        start_environment = dict(connection_environment)
        start_environment[_START_ACTOR_ENV] = actor_ref
        start_environment[_START_REASON_ENV] = request.decision_reason_text
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
            "--command",
            r"\getenv decision_actor_ref EA_START_ACTOR_REF",
            "--command",
            r"\getenv decision_reason_text EA_START_REASON_TEXT",
            "--command",
            _TARGET_STATE_START_SQL,
        ]
        try:
            result = runner(
                command,
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
                env=start_environment,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            raise PlannerExecutionError(
                "target-state start database command failed"
            ) from error
        if result.returncode != 0:
            raise PlannerExecutionError("target-state start database query failed")
        try:
            payload = json.loads(result.stdout.strip())
        except json.JSONDecodeError as error:
            raise PlannerExecutionError("target-state start returned invalid JSON") from error
        if not isinstance(payload, Mapping):
            raise PlannerExecutionError(
                "target-state start returned invalid start receipt"
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
                cast(str, payload.get("start_recorded_at")),
                "start_recorded_at",
            )
        except PlannerRequestError as error:
            raise PlannerExecutionError(
                "target-state start returned invalid start receipt"
            ) from error
        if (
            payload.get("architecture_transformation_id")
            != str(request.architecture_transformation_id)
            or payload.get("transformation_state_code") != "started"
            or payload.get("decision_request_id") != str(request.decision_request_id)
            or not isinstance(payload.get("replayed"), bool)
            or payload.get("next_action") != "monitor_transformation"
        ):
            raise PlannerExecutionError(
                "target-state start returned invalid start receipt"
            )
        return payload

    return writer
