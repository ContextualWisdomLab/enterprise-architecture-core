"""Purpose-bound command port for reassessing a closed data-management gap set."""

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

_RECHECK_PATH_PREFIX = "/v1/data-management-assessments/"
_RECHECK_PATH_SUFFIX = "/recheck"
_RECHECK_SQL = """
SELECT row_to_json(recheck_receipt)::text
FROM (
    SELECT
        requested.assessment_recheck_request_id,
        requested.outbox_event_id,
        requested.next_action
    FROM architecture_core.request_data_management_assessment_recheck_for_tenant(
        :'tenant_record_id'::uuid,
        :'data_management_assessment_projection_id'::uuid,
        :'trigger_evidence_acceptance_id'::uuid,
        :'decision_request_id'::uuid,
        :'requested_at'::timestamptz
    ) AS requested
) AS recheck_receipt;
""".strip()


@dataclass(frozen=True, slots=True)
class DataManagementRecheckRequest:
    """One explicit request to reassess an evidence-closed assessment projection."""

    data_management_assessment_projection_id: UUID
    trigger_evidence_acceptance_id: UUID
    decision_request_id: UUID
    requested_at: datetime

    @classmethod
    def from_values(
        cls,
        data_management_assessment_projection_id: str,
        trigger_evidence_acceptance_id: str,
        decision_request_id: str,
        requested_at: str,
    ) -> DataManagementRecheckRequest:
        """Validate canonical identities and request time before storage access."""

        return cls(
            data_management_assessment_projection_id=_parse_uuid7(
                data_management_assessment_projection_id,
                "data management assessment projection id",
            ),
            trigger_evidence_acceptance_id=_parse_uuid7(
                trigger_evidence_acceptance_id,
                "trigger evidence acceptance id",
            ),
            decision_request_id=_parse_uuid7(
                decision_request_id,
                "decision request id",
            ),
            requested_at=_parse_timestamp(requested_at, "requested_at"),
        )


def parse_data_management_recheck_request(
    path: str,
    payload: Mapping[str, object],
) -> DataManagementRecheckRequest:
    """Bind strict reassessment JSON to the projection named by the route."""

    parsed = urlparse(path)
    if parsed.query or parsed.fragment:
        raise PlannerRequestError(
            "data-management recheck path cannot contain query or fragment data"
        )
    route = parsed.path
    if not route.startswith(_RECHECK_PATH_PREFIX) or not route.endswith(
        _RECHECK_PATH_SUFFIX
    ):
        raise PlannerRequestError("data-management recheck path is invalid")
    assessment_id = route[len(_RECHECK_PATH_PREFIX) : -len(_RECHECK_PATH_SUFFIX)]
    if not assessment_id or "/" in assessment_id:
        raise PlannerRequestError("data-management recheck requires one assessment UUID")
    required_names = {
        "trigger_evidence_acceptance_id",
        "decision_request_id",
        "requested_at",
    }
    if set(payload) != required_names:
        raise PlannerRequestError(
            "data-management recheck body must contain only the documented fields"
        )
    if not all(isinstance(payload[name], str) for name in required_names):
        raise PlannerRequestError("data-management recheck fields must be JSON strings")
    return DataManagementRecheckRequest.from_values(
        assessment_id,
        str(payload["trigger_evidence_acceptance_id"]),
        str(payload["decision_request_id"]),
        str(payload["requested_at"]),
    )


def build_data_management_recheck_authorization_config(
    environ: Mapping[str, str],
) -> KeyverseAuthorizationConfig | None:
    """Build a Keyverse profile granting only assessment-recheck authority."""

    recheck_environment = dict(environ)
    recheck_environment["EA_READ_ROLES"] = environ.get(
        "EA_DATA_MANAGEMENT_RECHECK_ROLES",
        "",
    )
    return build_keyverse_authorization_config(recheck_environment)


def _unavailable_recheck_writer(
    context: AuthorizationContext,
    request: DataManagementRecheckRequest,
) -> Mapping[str, object]:
    """Reject reassessment when no safe PostgreSQL command port exists."""

    del context, request
    raise PlannerExecutionError("data-management recheck database is unavailable")


def build_data_management_recheck_writer(
    dsn: str | None,
    *,
    runner: CommandRunner = subprocess.run,
    base_environment: Mapping[str, str] | None = None,
):
    """Build the bounded reassessment writer without direct application-table SQL."""

    if not dsn:
        return _unavailable_recheck_writer
    connection_environment = _postgres_environment(dsn, base_environment)
    if connection_environment is None:
        return _unavailable_recheck_writer

    def writer(
        context: AuthorizationContext,
        request: DataManagementRecheckRequest,
    ) -> Mapping[str, object]:
        """Record one idempotent reassessment request and its transactional event."""

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
                "data_management_assessment_projection_id="
                f"{request.data_management_assessment_projection_id}"
            ),
            "--set",
            (
                "trigger_evidence_acceptance_id="
                f"{request.trigger_evidence_acceptance_id}"
            ),
            "--set",
            f"decision_request_id={request.decision_request_id}",
            "--set",
            f"requested_at={request.requested_at.isoformat()}",
            "--command",
            _RECHECK_SQL,
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
                "data-management recheck database command failed"
            ) from error
        if result.returncode != 0:
            raise PlannerExecutionError(
                "data-management recheck database query failed"
            )
        try:
            response = json.loads(result.stdout.strip())
        except json.JSONDecodeError as error:
            raise PlannerExecutionError(
                "data-management recheck returned invalid JSON"
            ) from error
        if not isinstance(response, Mapping):
            raise PlannerExecutionError(
                "data-management recheck returned invalid reassessment receipt"
            )
        try:
            _parse_uuid7(
                cast(str, response.get("assessment_recheck_request_id")),
                "assessment recheck request id",
            )
            _parse_uuid7(
                cast(str, response.get("outbox_event_id")),
                "outbox event id",
            )
        except PlannerRequestError as error:
            raise PlannerExecutionError(
                "data-management recheck returned invalid reassessment receipt"
            ) from error
        if response.get("next_action") != "await_assessment_recheck":
            raise PlannerExecutionError(
                "data-management recheck returned invalid reassessment receipt"
            )
        return response

    return writer
