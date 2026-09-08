"""Purpose-bound command port for replacing a gap-detected EA target state."""

from __future__ import annotations

import json
import re
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
_TARGET_STATE_REPLAN_PATH_SUFFIX = "/replan"
_REPLAN_ACTOR_ENV = "EA_REPLAN_ACTOR_REF"
_REPLAN_REASON_ENV = "EA_REPLAN_REASON_TEXT"
_REPLAN_TITLE_ENV = "EA_REPLAN_TITLE"
_REPLAN_DESCRIPTION_ENV = "EA_REPLAN_DESCRIPTION"
_CODE_PATTERN = re.compile(r"^[a-z][a-z0-9]+(?:_[a-z0-9]+)*$")
_TARGET_STATE_REPLAN_SQL = """
SELECT row_to_json(replan_receipt)::text
FROM (
    SELECT
        replanned.transformation_replan_record_id,
        replanned.predecessor_architecture_transformation_id,
        replanned.replacement_architecture_transformation_id,
        replanned.transformation_history_record_id,
        replanned.outbox_event_id,
        replanned.decision_request_id,
        replanned.replan_recorded_at,
        replanned.replan_replayed AS replayed,
        replanned.next_action
    FROM architecture_core.record_target_state_replan(
        :'tenant_record_id'::uuid,
        :'predecessor_architecture_transformation_id'::uuid,
        :'replacement_architecture_transformation_id'::uuid,
        :'decision_request_id'::uuid,
        :'architecture_scenario_id'::uuid,
        :'remediation_initiative_id'::uuid,
        :'transformation_code'::text,
        :'transformation_title'::text,
        :'transformation_description'::text,
        :'effective_at'::timestamptz,
        :'decision_actor_ref'::text,
        :'decision_reason_text'::text,
        :'evidence_record_id'::uuid
    ) AS replanned
) AS replan_receipt;
""".strip()


@dataclass(frozen=True, slots=True)
class TargetStateReplanRequest:
    """One human-authored replacement plan for a terminal gap-detected target state."""

    predecessor_architecture_transformation_id: UUID
    replacement_architecture_transformation_id: UUID
    decision_request_id: UUID
    architecture_scenario_id: UUID
    remediation_initiative_id: UUID
    transformation_code: str
    transformation_title: str
    transformation_description: str
    effective_at: datetime
    decision_reason_text: str
    evidence_record_id: UUID

    @classmethod
    def from_values(
        cls,
        predecessor_architecture_transformation_id: str,
        replacement_architecture_transformation_id: str,
        decision_request_id: str,
        architecture_scenario_id: str,
        remediation_initiative_id: str,
        transformation_code: str,
        transformation_title: str,
        transformation_description: str,
        effective_at: str,
        decision_reason_text: str,
        evidence_record_id: str,
    ) -> TargetStateReplanRequest:
        """Validate replacement-plan meaning before PostgreSQL is reachable."""

        predecessor_id = _parse_uuid7(
            predecessor_architecture_transformation_id,
            "predecessor architecture transformation id",
        )
        replacement_id = _parse_uuid7(
            replacement_architecture_transformation_id,
            "replacement architecture transformation id",
        )
        if predecessor_id == replacement_id:
            raise PlannerRequestError(
                "predecessor and replacement transformation ids must be distinct"
            )
        request_id = _parse_uuid7(decision_request_id, "decision request id")
        scenario_id = _parse_uuid7(architecture_scenario_id, "architecture scenario id")
        initiative_id = _parse_uuid7(
            remediation_initiative_id,
            "remediation initiative id",
        )
        evidence_id = _parse_uuid7(evidence_record_id, "evidence record id")
        effective_time = _parse_timestamp(effective_at, "effective_at")
        code = transformation_code.strip()
        title = transformation_title.strip()
        description = transformation_description.strip()
        reason = decision_reason_text.strip()
        if _CODE_PATTERN.fullmatch(code) is None or len(code) > 128:
            raise PlannerRequestError(
                "transformation_code must be a bounded lower snake_case identifier"
            )
        if not title or len(title) > 512:
            raise PlannerRequestError(
                "transformation_title must contain between 1 and 512 characters"
            )
        if not description or len(description) > 4096:
            raise PlannerRequestError(
                "transformation_description must contain between 1 and 4096 characters"
            )
        if not reason or len(reason) > 4096:
            raise PlannerRequestError(
                "decision_reason_text must contain between 1 and 4096 characters"
            )
        return cls(
            predecessor_architecture_transformation_id=predecessor_id,
            replacement_architecture_transformation_id=replacement_id,
            decision_request_id=request_id,
            architecture_scenario_id=scenario_id,
            remediation_initiative_id=initiative_id,
            transformation_code=code,
            transformation_title=title,
            transformation_description=description,
            effective_at=effective_time,
            decision_reason_text=reason,
            evidence_record_id=evidence_id,
        )


def parse_target_state_replan_request(
    path: str,
    payload: Mapping[str, object],
) -> TargetStateReplanRequest:
    """Bind strict replacement JSON to the terminal predecessor named by the path."""

    parsed = urlparse(path)
    if parsed.query or parsed.fragment:
        raise PlannerRequestError("replan path cannot contain query or fragment data")
    route = parsed.path
    if (
        not route.startswith(_TARGET_STATE_COMMAND_PATH_PREFIX)
        or not route.endswith(_TARGET_STATE_REPLAN_PATH_SUFFIX)
    ):
        raise PlannerRequestError("target-state replan path is invalid")
    prefix_length = len(_TARGET_STATE_COMMAND_PATH_PREFIX)
    suffix_length = len(_TARGET_STATE_REPLAN_PATH_SUFFIX)
    predecessor_id = route[prefix_length:-suffix_length]
    if not predecessor_id or "/" in predecessor_id:
        raise PlannerRequestError("target-state replan requires one predecessor UUID")
    required_names = {
        "decision_request_id",
        "replacement_architecture_transformation_id",
        "architecture_scenario_id",
        "remediation_initiative_id",
        "transformation_code",
        "transformation_title",
        "transformation_description",
        "effective_at",
        "decision_reason_text",
        "evidence_record_id",
    }
    if set(payload) != required_names:
        raise PlannerRequestError(
            "replan body must contain only the documented fields"
        )
    if not all(isinstance(payload[name], str) for name in required_names):
        raise PlannerRequestError("replan fields must be JSON strings")
    return TargetStateReplanRequest.from_values(
        predecessor_id,
        str(payload["replacement_architecture_transformation_id"]),
        str(payload["decision_request_id"]),
        str(payload["architecture_scenario_id"]),
        str(payload["remediation_initiative_id"]),
        str(payload["transformation_code"]),
        str(payload["transformation_title"]),
        str(payload["transformation_description"]),
        str(payload["effective_at"]),
        str(payload["decision_reason_text"]),
        str(payload["evidence_record_id"]),
    )


def build_replan_authorization_config(
    environ: Mapping[str, str],
) -> KeyverseAuthorizationConfig | None:
    """Build a Keyverse profile granting only target-state replanning authority."""

    replan_environment = dict(environ)
    replan_environment["EA_READ_ROLES"] = environ.get("EA_REPLAN_ROLES", "")
    return build_keyverse_authorization_config(replan_environment)


def _unavailable_replan_writer(
    context: AuthorizationContext,
    request: TargetStateReplanRequest,
) -> Mapping[str, object]:
    """Reject replanning when no safe PostgreSQL command port exists."""

    del context, request
    raise PlannerExecutionError("target-state replan database is unavailable")


def build_target_state_replan_writer(
    dsn: str | None,
    *,
    runner: CommandRunner = subprocess.run,
    base_environment: Mapping[str, str] | None = None,
):
    """Build the purpose-bound replanning writer without direct table mutation."""

    if not dsn:
        return _unavailable_replan_writer
    connection_environment = _postgres_environment(dsn, base_environment)
    if connection_environment is None:
        return _unavailable_replan_writer

    def writer(
        context: AuthorizationContext,
        request: TargetStateReplanRequest,
    ) -> Mapping[str, object]:
        """Create one idempotent replacement proposal and immutable replan evidence."""

        actor_ref = f"keyverse:{context.issuer_uri}#{context.subject_id}"
        if len(actor_ref) > 2048:
            raise PlannerExecutionError("verified actor reference is too long")
        replan_environment = dict(connection_environment)
        replan_environment[_REPLAN_ACTOR_ENV] = actor_ref
        replan_environment[_REPLAN_REASON_ENV] = request.decision_reason_text
        replan_environment[_REPLAN_TITLE_ENV] = request.transformation_title
        replan_environment[_REPLAN_DESCRIPTION_ENV] = request.transformation_description
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
            (
                "predecessor_architecture_transformation_id="
                f"{request.predecessor_architecture_transformation_id}"
            ),
            "--set",
            (
                "replacement_architecture_transformation_id="
                f"{request.replacement_architecture_transformation_id}"
            ),
            "--set",
            f"decision_request_id={request.decision_request_id}",
            "--set",
            f"architecture_scenario_id={request.architecture_scenario_id}",
            "--set",
            f"remediation_initiative_id={request.remediation_initiative_id}",
            "--set",
            f"transformation_code={request.transformation_code}",
            "--set",
            f"effective_at={request.effective_at.isoformat()}",
            "--set",
            f"evidence_record_id={request.evidence_record_id}",
            "--command",
            r"\getenv transformation_title EA_REPLAN_TITLE",
            "--command",
            r"\getenv transformation_description EA_REPLAN_DESCRIPTION",
            "--command",
            r"\getenv decision_actor_ref EA_REPLAN_ACTOR_REF",
            "--command",
            r"\getenv decision_reason_text EA_REPLAN_REASON_TEXT",
            "--command",
            _TARGET_STATE_REPLAN_SQL,
        ]
        try:
            result = runner(
                command,
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
                env=replan_environment,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            raise PlannerExecutionError(
                "target-state replan database command failed"
            ) from error
        if result.returncode != 0:
            raise PlannerExecutionError("target-state replan database query failed")
        try:
            response = json.loads(result.stdout.strip())
        except json.JSONDecodeError as error:
            raise PlannerExecutionError(
                "target-state replan returned invalid JSON"
            ) from error
        if not isinstance(response, Mapping):
            raise PlannerExecutionError(
                "target-state replan returned invalid replan receipt"
            )
        try:
            _parse_uuid7(
                cast(str, response.get("transformation_replan_record_id")),
                "transformation replan record id",
            )
            _parse_uuid7(
                cast(str, response.get("transformation_history_record_id")),
                "transformation history record id",
            )
            _parse_uuid7(
                cast(str, response.get("outbox_event_id")),
                "outbox event id",
            )
            _parse_timestamp(
                cast(str, response.get("replan_recorded_at")),
                "replan_recorded_at",
            )
        except PlannerRequestError as error:
            raise PlannerExecutionError(
                "target-state replan returned invalid replan receipt"
            ) from error
        if (
            response.get("predecessor_architecture_transformation_id")
            != str(request.predecessor_architecture_transformation_id)
            or response.get("replacement_architecture_transformation_id")
            != str(request.replacement_architecture_transformation_id)
            or response.get("decision_request_id") != str(request.decision_request_id)
            or not isinstance(response.get("replayed"), bool)
            or response.get("next_action") != "approve_target_state"
        ):
            raise PlannerExecutionError(
                "target-state replan returned invalid replan receipt"
            )
        return response

    return writer
