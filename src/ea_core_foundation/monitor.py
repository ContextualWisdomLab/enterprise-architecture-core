"""Purpose-bound read port for target-state monitoring freshness decisions."""

from __future__ import annotations

import json
import subprocess
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import parse_qsl, urlparse
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

_TARGET_STATE_MONITORING_PATH_PREFIX = "/v1/architecture-transformations/"
_TARGET_STATE_MONITORING_PATH_SUFFIX = "/monitoring"
_TARGET_STATE_MONITORING_SQL = """
SELECT row_to_json(monitoring_status)::text
FROM architecture_core.read_target_state_monitoring_status(
    :'tenant_record_id'::uuid,
    :'architecture_transformation_id'::uuid,
    :'valid_at'::timestamptz,
    :'recorded_at'::timestamptz,
    :'max_evidence_age_days'::integer
) AS monitoring_status;
""".strip()
_MONITORING_ACTIONS = {
    "current": "continue_monitoring",
    "stale": "collect_new_target_state_evidence",
    "gap_detected": "replan_target_state",
}


@dataclass(frozen=True, slots=True)
class TargetStateMonitoringRequest:
    """One exact bitemporal freshness query for a verified target state."""

    architecture_transformation_id: UUID
    valid_at: datetime
    recorded_at: datetime
    max_evidence_age_days: int

    @classmethod
    def from_values(
        cls,
        architecture_transformation_id: str,
        valid_at: str,
        recorded_at: str,
        max_evidence_age_days: int = 90,
    ) -> TargetStateMonitoringRequest:
        """Validate canonical identity, time cutoffs, and bounded freshness policy."""

        transformation_id = _parse_uuid7(
            architecture_transformation_id,
            "architecture transformation id",
        )
        valid_time = _parse_timestamp(valid_at, "valid_at")
        recorded_time = _parse_timestamp(recorded_at, "recorded_at")
        if max_evidence_age_days < 1 or max_evidence_age_days > 3650:
            raise PlannerRequestError(
                "max_evidence_age_days must be between 1 and 3650"
            )
        return cls(
            architecture_transformation_id=transformation_id,
            valid_at=valid_time,
            recorded_at=recorded_time,
            max_evidence_age_days=max_evidence_age_days,
        )


def parse_target_state_monitoring_request(path: str) -> TargetStateMonitoringRequest:
    """Parse one monitoring route without duplicate or unknown query parameters."""

    parsed = urlparse(path)
    route = parsed.path
    if (
        not route.startswith(_TARGET_STATE_MONITORING_PATH_PREFIX)
        or not route.endswith(_TARGET_STATE_MONITORING_PATH_SUFFIX)
    ):
        raise PlannerRequestError("target-state monitoring path is invalid")
    prefix_length = len(_TARGET_STATE_MONITORING_PATH_PREFIX)
    suffix_length = len(_TARGET_STATE_MONITORING_PATH_SUFFIX)
    transformation_id = route[prefix_length:-suffix_length]
    if not transformation_id or "/" in transformation_id:
        raise PlannerRequestError(
            "target-state monitoring requires one transformation UUID"
        )

    pairs = parse_qsl(parsed.query, keep_blank_values=True)
    allowed_names = {"valid_at", "recorded_at", "max_evidence_age_days"}
    if any(name not in allowed_names for name, _ in pairs):
        raise PlannerRequestError(
            "target-state monitoring query contains unknown parameters"
        )
    values: dict[str, str] = {}
    for name, value in pairs:
        if name in values:
            raise PlannerRequestError(
                f"duplicate monitoring query parameter: {name}"
            )
        values[name] = value
    if not values.get("valid_at") or not values.get("recorded_at"):
        raise PlannerRequestError("valid_at and recorded_at are required")
    raw_max_age = values.get("max_evidence_age_days", "90")
    try:
        max_age = int(raw_max_age)
    except ValueError as error:
        raise PlannerRequestError(
            "max_evidence_age_days must be an integer"
        ) from error
    return TargetStateMonitoringRequest.from_values(
        transformation_id,
        values["valid_at"],
        values["recorded_at"],
        max_age,
    )


def build_monitoring_authorization_config(
    environ: Mapping[str, str],
) -> KeyverseAuthorizationConfig | None:
    """Build a Keyverse profile granting only target-state monitoring reads."""

    monitoring_environment = dict(environ)
    monitoring_environment["EA_READ_ROLES"] = environ.get("EA_MONITOR_ROLES", "")
    return build_keyverse_authorization_config(monitoring_environment)


def _unavailable_monitoring_reader(
    context: AuthorizationContext,
    request: TargetStateMonitoringRequest,
) -> Mapping[str, object]:
    """Reject monitoring reads when no safe PostgreSQL read port exists."""

    del context, request
    raise PlannerExecutionError("target-state monitoring database is unavailable")


def build_target_state_monitoring_reader(
    dsn: str | None,
    *,
    runner: CommandRunner = subprocess.run,
    base_environment: Mapping[str, str] | None = None,
):
    """Build a tenant-bound monitoring reader without direct application-table SQL."""

    if not dsn:
        return _unavailable_monitoring_reader
    connection_environment = _postgres_environment(dsn, base_environment)
    if connection_environment is None:
        return _unavailable_monitoring_reader

    def reader(
        context: AuthorizationContext,
        request: TargetStateMonitoringRequest,
    ) -> Mapping[str, object]:
        """Return one exact verification-freshness decision from PostgreSQL."""

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
            f"valid_at={request.valid_at.isoformat()}",
            "--set",
            f"recorded_at={request.recorded_at.isoformat()}",
            "--set",
            f"max_evidence_age_days={request.max_evidence_age_days}",
            "--command",
            _TARGET_STATE_MONITORING_SQL,
        ]
        try:
            result = runner(
                command,
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
                env=connection_environment,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            raise PlannerExecutionError(
                "target-state monitoring database command failed"
            ) from error
        if result.returncode != 0:
            raise PlannerExecutionError("target-state monitoring database query failed")
        try:
            payload = json.loads(result.stdout.strip())
        except json.JSONDecodeError as error:
            raise PlannerExecutionError(
                "target-state monitoring returned invalid JSON"
            ) from error
        if not isinstance(payload, Mapping):
            raise PlannerExecutionError(
                "target-state monitoring returned invalid monitoring status"
            )

        state = payload.get("monitoring_state_code")
        expected_action = _MONITORING_ACTIONS.get(state)
        evidence_id = payload.get("evidence_record_id")
        evidence_age_days = payload.get("evidence_age_days")
        try:
            _parse_uuid7(str(evidence_id), "evidence record id")
            _parse_timestamp(
                str(payload.get("verification_effective_at")),
                "verification_effective_at",
            )
            _parse_timestamp(
                str(payload.get("verification_recorded_at")),
                "verification_recorded_at",
            )
        except PlannerRequestError as error:
            raise PlannerExecutionError(
                "target-state monitoring returned invalid monitoring status"
            ) from error
        if (
            payload.get("architecture_transformation_id")
            != str(request.architecture_transformation_id)
            or payload.get("verification_state_code") not in {"verified", "gap_detected"}
            or not isinstance(evidence_age_days, int)
            or isinstance(evidence_age_days, bool)
            or evidence_age_days < 0
            or expected_action is None
            or payload.get("next_action") != expected_action
            or (state == "gap_detected" and payload.get("verification_state_code") != "gap_detected")
            or (state in {"current", "stale"} and payload.get("verification_state_code") != "verified")
        ):
            raise PlannerExecutionError(
                "target-state monitoring returned invalid monitoring status"
            )
        return payload

    return reader
