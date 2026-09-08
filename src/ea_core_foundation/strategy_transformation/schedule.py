"""Purpose-bound command port for scheduling an approved EA transformation."""

from __future__ import annotations

import json
import subprocess
from collections.abc import Callable, Mapping
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
_TARGET_STATE_SCHEDULE_PATH_SUFFIX = "/schedule"
_SCHEDULE_ACTOR_ENV = "EA_SCHEDULE_ACTOR_REF"
_SCHEDULE_REASON_ENV = "EA_SCHEDULE_REASON_TEXT"
_TARGET_STATE_SCHEDULE_SQL = """
SELECT row_to_json(schedule_receipt)::text
FROM (
    SELECT
        schedule.transformation_schedule_record_id,
        schedule.architecture_transformation_id,
        schedule.initiative_milestone_id,
        schedule.outbox_event_id,
        schedule.decision_request_id,
        schedule.milestone_target_at,
        schedule.schedule_recorded_at,
        schedule.schedule_replayed AS replayed,
        schedule.next_action
    FROM architecture_core.schedule_transformation(
        :'tenant_record_id'::uuid,
        :'architecture_transformation_id'::uuid,
        :'decision_request_id'::uuid,
        :'initiative_milestone_id'::uuid,
        :'effective_at'::timestamptz,
        :'decision_actor_ref'::text,
        :'decision_reason_text'::text,
        :'evidence_record_id'::uuid
    ) AS schedule
) AS schedule_receipt;
""".strip()


@dataclass(frozen=True, slots=True)
class TargetStateScheduleRequest:
    """One immutable decision binding an approved transformation to a milestone."""

    architecture_transformation_id: UUID
    decision_request_id: UUID
    initiative_milestone_id: UUID
    effective_at: datetime
    decision_reason_text: str
    evidence_record_id: UUID

    @classmethod
    def from_values(
        cls,
        architecture_transformation_id: str,
        decision_request_id: str,
        initiative_milestone_id: str,
        effective_at: str,
        decision_reason_text: str,
        evidence_record_id: str,
    ) -> TargetStateScheduleRequest:
        """Validate a schedule command before verified authority reaches PostgreSQL."""

        transformation_id = _parse_uuid7(
            architecture_transformation_id,
            "architecture transformation id",
        )
        request_id = _parse_uuid7(decision_request_id, "decision request id")
        milestone_id = _parse_uuid7(
            initiative_milestone_id,
            "initiative milestone id",
        )
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
            initiative_milestone_id=milestone_id,
            effective_at=effective_time,
            decision_reason_text=reason,
            evidence_record_id=evidence_id,
        )


TargetStateScheduleWriter = Callable[
    [AuthorizationContext, TargetStateScheduleRequest], Mapping[str, object]
]


def parse_target_state_schedule_request(
    path: str,
    payload: Mapping[str, object],
) -> TargetStateScheduleRequest:
    """Bind strict JSON to the one transformation named by the schedule path."""

    parsed = urlparse(path)
    if parsed.query or parsed.fragment:
        raise PlannerRequestError("schedule path cannot contain query or fragment data")
    route = parsed.path
    if (
        not route.startswith(_TARGET_STATE_COMMAND_PATH_PREFIX)
        or not route.endswith(_TARGET_STATE_SCHEDULE_PATH_SUFFIX)
    ):
        raise PlannerRequestError("target-state schedule path is invalid")
    prefix_length = len(_TARGET_STATE_COMMAND_PATH_PREFIX)
    suffix_length = len(_TARGET_STATE_SCHEDULE_PATH_SUFFIX)
    transformation_id = route[prefix_length:-suffix_length]
    if not transformation_id or "/" in transformation_id:
        raise PlannerRequestError(
            "target-state schedule requires one transformation UUID"
        )
    required_names = {
        "decision_request_id",
        "initiative_milestone_id",
        "effective_at",
        "decision_reason_text",
        "evidence_record_id",
    }
    if set(payload) != required_names:
        raise PlannerRequestError(
            "schedule body must contain only the documented fields"
        )
    if not all(isinstance(payload[name], str) for name in required_names):
        raise PlannerRequestError("schedule fields must be JSON strings")
    return TargetStateScheduleRequest.from_values(
        transformation_id,
        str(payload["decision_request_id"]),
        str(payload["initiative_milestone_id"]),
        str(payload["effective_at"]),
        str(payload["decision_reason_text"]),
        str(payload["evidence_record_id"]),
    )


def build_schedule_authorization_config(
    environ: Mapping[str, str],
) -> KeyverseAuthorizationConfig | None:
    """Build a Keyverse RP profile whose roles grant only scheduling authority."""

    schedule_environment = dict(environ)
    schedule_environment["EA_READ_ROLES"] = environ.get("EA_SCHEDULE_ROLES", "")
    return build_keyverse_authorization_config(schedule_environment)


def _unavailable_schedule_writer(
    context: AuthorizationContext,
    request: TargetStateScheduleRequest,
) -> Mapping[str, object]:
    """Reject scheduling when no safe PostgreSQL command port is configured."""

    del context, request
    raise PlannerExecutionError("target-state schedule database is unavailable")


def build_target_state_schedule_writer(
    dsn: str | None,
    *,
    runner: CommandRunner = subprocess.run,
    base_environment: Mapping[str, str] | None = None,
):
    """Build the purpose-bound scheduler without granting direct table mutation."""

    if not dsn:
        return _unavailable_schedule_writer
    connection_environment = _postgres_environment(dsn, base_environment)
    if connection_environment is None:
        return _unavailable_schedule_writer

    def writer(
        context: AuthorizationContext,
        request: TargetStateScheduleRequest,
    ) -> Mapping[str, object]:
        """Execute one idempotent milestone binding through the governed DB function."""

        actor_ref = f"keyverse:{context.issuer_uri}#{context.subject_id}"
        if len(actor_ref) > 2048:
            raise PlannerExecutionError("verified actor reference is too long")
        schedule_environment = dict(connection_environment)
        schedule_environment[_SCHEDULE_ACTOR_ENV] = actor_ref
        schedule_environment[_SCHEDULE_REASON_ENV] = request.decision_reason_text
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
            f"initiative_milestone_id={request.initiative_milestone_id}",
            "--set",
            f"effective_at={request.effective_at.isoformat()}",
            "--set",
            f"evidence_record_id={request.evidence_record_id}",
            "--command",
            r"\getenv decision_actor_ref EA_SCHEDULE_ACTOR_REF",
            "--command",
            r"\getenv decision_reason_text EA_SCHEDULE_REASON_TEXT",
            "--command",
            _TARGET_STATE_SCHEDULE_SQL,
        ]
        try:
            result = runner(
                command,
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
                env=schedule_environment,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            raise PlannerExecutionError(
                "target-state schedule database command failed"
            ) from error
        if result.returncode != 0:
            raise PlannerExecutionError("target-state schedule database query failed")
        try:
            payload = json.loads(result.stdout.strip())
        except json.JSONDecodeError as error:
            raise PlannerExecutionError(
                "target-state schedule returned invalid JSON"
            ) from error
        if not isinstance(payload, Mapping):
            raise PlannerExecutionError(
                "target-state schedule returned invalid schedule receipt"
            )
        try:
            _parse_uuid7(
                cast(str, payload.get("transformation_schedule_record_id")),
                "transformation schedule record id",
            )
            _parse_timestamp(
                cast(str, payload.get("milestone_target_at")),
                "milestone_target_at",
            )
            _parse_timestamp(
                cast(str, payload.get("schedule_recorded_at")),
                "schedule_recorded_at",
            )
        except PlannerRequestError as error:
            raise PlannerExecutionError(
                "target-state schedule returned invalid schedule receipt"
            ) from error
        if (
            payload.get("architecture_transformation_id")
            != str(request.architecture_transformation_id)
            or payload.get("initiative_milestone_id")
            != str(request.initiative_milestone_id)
            or payload.get("decision_request_id") != str(request.decision_request_id)
            or not isinstance(payload.get("replayed"), bool)
            or payload.get("next_action") != "start_transformation"
        ):
            raise PlannerExecutionError(
                "target-state schedule returned invalid schedule receipt"
            )
        return payload

    return writer
