"""Purpose-bound read port for an EA-owned data-management reassessment."""

from __future__ import annotations

import json
import subprocess
from collections.abc import Mapping
from dataclasses import dataclass
from typing import cast
from urllib.parse import urlparse
from uuid import UUID

from ..authorization import AuthorizationContext, KeyverseAuthorizationConfig
from ..service import (
    CommandRunner,
    PlannerExecutionError,
    PlannerRequestError,
    _parse_uuid7,
    _postgres_environment,
    build_keyverse_authorization_config,
)

_RECHECK_STATUS_PATH_PREFIX = "/v1/data-management-assessment-rechecks/"
_RECHECK_STATUS_SQL = """
SELECT row_to_json(recheck_status)::text
FROM architecture_core.read_data_management_assessment_recheck_status(
    :'tenant_record_id'::uuid,
    :'assessment_recheck_request_id'::uuid
) AS recheck_status;
""".strip()
_RECHECK_STATUS_FIELDS = {
    "assessment_recheck_request_id",
    "data_management_assessment_projection_id",
    "successor_assessment_projection_id",
    "successor_truth_status_code",
    "recheck_state_code",
    "successor_readiness_code",
    "successor_overall_score_basis_points",
    "successor_missing_evidence_count",
    "next_action",
}
_TRUSTED_SUCCESSOR_TRUTH = {"authoritative", "observed"}
_REVIEW_REQUIRED_SUCCESSOR_TRUTH = {
    "inferred",
    "proposed",
    "superseded",
    "rejected",
}
_ALL_SUCCESSOR_TRUTH = _TRUSTED_SUCCESSOR_TRUTH | _REVIEW_REQUIRED_SUCCESSOR_TRUTH


@dataclass(frozen=True, slots=True)
class DataManagementRecheckStatusRequest:
    """One tenant-scoped request to follow an accepted reassessment command."""

    assessment_recheck_request_id: UUID

    @classmethod
    def from_value(
        cls,
        assessment_recheck_request_id: str,
    ) -> DataManagementRecheckStatusRequest:
        """Validate the reassessment-request identity before storage access."""

        return cls(
            assessment_recheck_request_id=_parse_uuid7(
                assessment_recheck_request_id,
                "assessment recheck request id",
            )
        )


def parse_data_management_recheck_status_request(
    path: str,
) -> DataManagementRecheckStatusRequest:
    """Bind one strict local-origin reassessment-status resource path."""

    parsed = urlparse(path)
    if parsed.scheme or parsed.netloc or parsed.query or parsed.fragment:
        raise PlannerRequestError(
            "data-management recheck status path must use local origin form without "
            "authority, query, or fragment data"
        )
    route = parsed.path
    if not route.startswith(_RECHECK_STATUS_PATH_PREFIX):
        raise PlannerRequestError("data-management recheck status path is invalid")
    recheck_id = route[len(_RECHECK_STATUS_PATH_PREFIX) :]
    if not recheck_id or "/" in recheck_id:
        raise PlannerRequestError(
            "data-management recheck status requires one reassessment request UUID"
        )
    return DataManagementRecheckStatusRequest.from_value(recheck_id)


def build_data_management_recheck_status_authorization_config(
    environ: Mapping[str, str],
) -> KeyverseAuthorizationConfig | None:
    """Build a Keyverse profile granting only reassessment-status read authority."""

    read_environment = dict(environ)
    read_environment["EA_READ_ROLES"] = environ.get(
        "EA_DATA_MANAGEMENT_RECHECK_READ_ROLES",
        "",
    )
    return build_keyverse_authorization_config(read_environment)


def _unavailable_recheck_status_reader(
    context: AuthorizationContext,
    request: DataManagementRecheckStatusRequest,
) -> Mapping[str, object]:
    """Reject status reads when no safe PostgreSQL read port exists."""

    del context, request
    raise PlannerExecutionError(
        "data-management recheck status database is unavailable"
    )


def _parse_response_uuid(
    response: Mapping[str, object],
    field_name: str,
) -> UUID:
    """Return one canonical UUIDv7 response field or fail closed."""

    value = response.get(field_name)
    if not isinstance(value, str):
        raise PlannerExecutionError(
            "data-management recheck status returned invalid status evidence"
        )
    try:
        return _parse_uuid7(value, field_name.replace("_", " "))
    except PlannerRequestError as error:
        raise PlannerExecutionError(
            "data-management recheck status returned invalid status evidence"
        ) from error


def _validate_recheck_status_response(
    response: object,
    request: DataManagementRecheckStatusRequest,
) -> Mapping[str, object]:
    """Validate exact shape, truth origin, and buyer action for one status receipt."""

    if not isinstance(response, Mapping) or set(response) != _RECHECK_STATUS_FIELDS:
        raise PlannerExecutionError(
            "data-management recheck status returned invalid status evidence"
        )
    response_recheck_id = _parse_response_uuid(
        response,
        "assessment_recheck_request_id",
    )
    if response_recheck_id != request.assessment_recheck_request_id:
        raise PlannerExecutionError(
            "data-management recheck status returned invalid status evidence"
        )
    _parse_response_uuid(response, "data_management_assessment_projection_id")

    state = response.get("recheck_state_code")
    truth = response.get("successor_truth_status_code")
    readiness = response.get("successor_readiness_code")
    action = response.get("next_action")
    successor = response.get("successor_assessment_projection_id")
    score = response.get("successor_overall_score_basis_points")
    missing_count = response.get("successor_missing_evidence_count")

    if state == "awaiting_result":
        if any(
            value is not None
            for value in (successor, truth, readiness, score, missing_count)
        ):
            raise PlannerExecutionError(
                "data-management recheck status returned invalid status evidence"
            )
        if action != "await_assessment_recheck":
            raise PlannerExecutionError(
                "data-management recheck status returned invalid status evidence"
            )
        return response

    if successor is None:
        raise PlannerExecutionError(
            "data-management recheck status returned invalid status evidence"
        )
    _parse_response_uuid(response, "successor_assessment_projection_id")
    if not isinstance(truth, str) or truth not in _ALL_SUCCESSOR_TRUTH:
        raise PlannerExecutionError(
            "data-management recheck status returned invalid status evidence"
        )
    if not isinstance(readiness, str) or readiness not in {
        "evidence_gap",
        "evidence_complete",
    }:
        raise PlannerExecutionError(
            "data-management recheck status returned invalid status evidence"
        )
    if type(score) is not int or not 0 <= cast(int, score) <= 10000:
        raise PlannerExecutionError(
            "data-management recheck status returned invalid status evidence"
        )
    if type(missing_count) is not int or cast(int, missing_count) < 0:
        raise PlannerExecutionError(
            "data-management recheck status returned invalid status evidence"
        )
    if readiness == "evidence_gap":
        if cast(int, missing_count) == 0:
            raise PlannerExecutionError(
                "data-management recheck status returned invalid status evidence"
            )
    elif cast(int, missing_count) != 0:
        raise PlannerExecutionError(
            "data-management recheck status returned invalid status evidence"
        )

    if state == "review_required":
        if (
            truth not in _REVIEW_REQUIRED_SUCCESSOR_TRUTH
            or action != "review_assessment_recheck_evidence"
        ):
            raise PlannerExecutionError(
                "data-management recheck status returned invalid status evidence"
            )
        return response

    if truth not in _TRUSTED_SUCCESSOR_TRUTH:
        raise PlannerExecutionError(
            "data-management recheck status returned invalid status evidence"
        )
    expected_action = {
        "evidence_gap": "plan_remaining_assessment_gap",
        "evidence_complete": "close_assessment_improvement_loop",
    }[readiness]
    if state != readiness or action != expected_action:
        raise PlannerExecutionError(
            "data-management recheck status returned invalid status evidence"
        )
    return response


def build_data_management_recheck_status_reader(
    dsn: str | None,
    *,
    runner: CommandRunner = subprocess.run,
    base_environment: Mapping[str, str] | None = None,
):
    """Build a bounded status reader without granting direct application-table SQL."""

    if not dsn:
        return _unavailable_recheck_status_reader
    connection_environment = _postgres_environment(dsn, base_environment)
    if connection_environment is None:
        return _unavailable_recheck_status_reader

    def reader(
        context: AuthorizationContext,
        request: DataManagementRecheckStatusRequest,
    ) -> Mapping[str, object]:
        """Read one reassessment status and validate its buyer action semantics."""

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
                "assessment_recheck_request_id="
                f"{request.assessment_recheck_request_id}"
            ),
            "--command",
            _RECHECK_STATUS_SQL,
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
                "data-management recheck status database command failed"
            ) from error
        if result.returncode != 0:
            raise PlannerExecutionError(
                "data-management recheck status database query failed"
            )
        try:
            response = json.loads(result.stdout.strip())
        except json.JSONDecodeError as error:
            raise PlannerExecutionError(
                "data-management recheck status returned invalid JSON"
            ) from error
        return _validate_recheck_status_response(response, request)

    return reader
