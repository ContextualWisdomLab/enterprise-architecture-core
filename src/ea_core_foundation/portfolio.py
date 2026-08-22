"""Purpose-bound read port for one architecture object's portfolio assessments."""

from __future__ import annotations

import json
import re
import subprocess
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from math import isfinite
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

_PORTFOLIO_ASSESSMENT_PATH_PREFIX = "/v1/architecture-objects/"
_PORTFOLIO_ASSESSMENT_PATH_SUFFIX = "/portfolio-assessments"
_PORTFOLIO_ASSESSMENT_SQL = """
SELECT COALESCE(
    json_agg(to_jsonb(assessment_result) ORDER BY
        assessment_result.assessment_framework_code,
        assessment_result.assessment_cycle_code,
        assessment_result.assessment_dimension_code,
        assessment_result.valid_from,
        assessment_result.recorded_at
    ),
    '[]'::json
)::text
FROM architecture_core.read_portfolio_assessment_for_tenant(
    :'tenant_record_id'::uuid,
    :'architecture_object_id'::uuid,
    :'valid_at'::timestamptz,
    :'recorded_at'::timestamptz,
    NULLIF(:'framework_code', ''),
    NULLIF(:'cycle_code', '')
) AS assessment_result;
""".strip()
_PORTFOLIO_ASSESSMENT_FIELDS = frozenset(
    {
        "architecture_object_id",
        "assessment_framework_code",
        "assessment_framework_title",
        "assessment_framework_version_label",
        "assessment_scale_code",
        "assessment_dimension_code",
        "assessment_dimension_title",
        "assessment_cycle_code",
        "assessment_cycle_title",
        "score_value",
        "score_label",
        "truth_status_code",
        "evidence_record_id",
        "valid_from",
        "valid_to",
        "recorded_at",
    }
)
_TRUTH_STATUS_CODES = {"authoritative", "observed", "inferred", "proposed"}
_CODE_PATTERN = re.compile(r"^[a-z][a-z0-9]+(?:_[a-z0-9]+)*$")


@dataclass(frozen=True, slots=True)
class PortfolioAssessmentRequest:
    """One exact tenant-scoped bitemporal portfolio assessment query."""

    architecture_object_id: UUID
    valid_at: datetime
    recorded_at: datetime
    framework_code: str | None
    cycle_code: str | None


def _parse_optional_code(value: str | None, field_name: str) -> str | None:
    """Validate one optional lower-snake framework or cycle selector."""

    if value is None:
        return None
    if not 2 <= len(value) <= 63 or _CODE_PATTERN.fullmatch(value) is None:
        raise PlannerRequestError(f"{field_name} must be a lower-snake code")
    return value


def parse_portfolio_assessment_request(path: str) -> PortfolioAssessmentRequest:
    """Bind one strict local-origin portfolio assessment query."""

    parsed = urlparse(path)
    if parsed.scheme or parsed.netloc or parsed.fragment:
        raise PlannerRequestError(
            "portfolio assessment path must use local origin form without authority "
            "or fragment data"
        )
    route = parsed.path
    if not route.startswith(_PORTFOLIO_ASSESSMENT_PATH_PREFIX) or not route.endswith(
        _PORTFOLIO_ASSESSMENT_PATH_SUFFIX
    ):
        raise PlannerRequestError("portfolio assessment path is invalid")
    object_id = route[
        len(_PORTFOLIO_ASSESSMENT_PATH_PREFIX) : -len(_PORTFOLIO_ASSESSMENT_PATH_SUFFIX)
    ]
    if not object_id or "/" in object_id:
        raise PlannerRequestError(
            "portfolio assessment requires one architecture object UUID"
        )

    pairs = parse_qsl(parsed.query, keep_blank_values=True)
    allowed_names = {"valid_at", "recorded_at", "framework_code", "cycle_code"}
    if any(name not in allowed_names for name, _ in pairs):
        raise PlannerRequestError(
            "portfolio assessment query contains unknown parameters"
        )
    values: dict[str, str] = {}
    for name, value in pairs:
        if name in values:
            raise PlannerRequestError(
                f"duplicate portfolio assessment parameter: {name}"
            )
        values[name] = value
    if not values.get("valid_at") or not values.get("recorded_at"):
        raise PlannerRequestError("valid_at and recorded_at are required")
    return PortfolioAssessmentRequest(
        architecture_object_id=_parse_uuid7(object_id, "architecture object id"),
        valid_at=_parse_timestamp(values["valid_at"], "valid_at"),
        recorded_at=_parse_timestamp(values["recorded_at"], "recorded_at"),
        framework_code=_parse_optional_code(
            values.get("framework_code"), "framework_code"
        ),
        cycle_code=_parse_optional_code(values.get("cycle_code"), "cycle_code"),
    )


def build_portfolio_assessment_authorization_config(
    environ: Mapping[str, str],
) -> KeyverseAuthorizationConfig | None:
    """Build a Keyverse profile granting only portfolio assessment read authority."""

    read_environment = dict(environ)
    read_environment["EA_READ_ROLES"] = environ.get(
        "EA_PORTFOLIO_ASSESSMENT_READ_ROLES",
        "",
    )
    return build_keyverse_authorization_config(read_environment)


def _unavailable_portfolio_assessment_reader(
    context: AuthorizationContext,
    request: PortfolioAssessmentRequest,
) -> Mapping[str, object]:
    """Reject reads when no safe PostgreSQL read port exists."""

    del context, request
    raise PlannerExecutionError("portfolio assessment database is unavailable")


def _parse_response_uuid(value: object, field_name: str) -> UUID:
    """Validate one canonical UUIDv7 returned by the purpose-bound SQL port."""

    if not isinstance(value, str):
        raise PlannerExecutionError("portfolio assessment returned invalid evidence")
    try:
        return _parse_uuid7(value, field_name.replace("_", " "))
    except PlannerRequestError as error:
        raise PlannerExecutionError(
            "portfolio assessment returned invalid evidence"
        ) from error


def _parse_response_timestamp(value: object) -> datetime:
    """Validate one timezone-aware PostgreSQL JSON timestamp."""

    if not isinstance(value, str):
        raise PlannerExecutionError("portfolio assessment returned invalid evidence")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise PlannerExecutionError(
            "portfolio assessment returned invalid evidence"
        ) from error
    if parsed.tzinfo is None:
        raise PlannerExecutionError("portfolio assessment returned invalid evidence")
    return parsed


def _validate_portfolio_assessment_response(
    response: object,
    request: PortfolioAssessmentRequest,
) -> Mapping[str, object]:
    """Validate exact assessment row shape and preserve the requested cutoffs."""

    if not isinstance(response, list):
        raise PlannerExecutionError("portfolio assessment returned invalid JSON")
    assessments: list[Mapping[str, object]] = []
    for row in response:
        if not isinstance(row, Mapping) or set(row) != _PORTFOLIO_ASSESSMENT_FIELDS:
            raise PlannerExecutionError(
                "portfolio assessment returned invalid evidence"
            )
        if _parse_response_uuid(
            row.get("architecture_object_id"), "architecture object id"
        ) != (
            request.architecture_object_id
        ):
            raise PlannerExecutionError(
                "portfolio assessment returned invalid evidence"
            )
        for field_name in (
            "assessment_framework_code",
            "assessment_framework_title",
            "assessment_framework_version_label",
            "assessment_scale_code",
            "assessment_dimension_code",
            "assessment_dimension_title",
            "assessment_cycle_code",
            "assessment_cycle_title",
            "score_label",
        ):
            if not isinstance(row.get(field_name), str) or not row[field_name]:
                raise PlannerExecutionError(
                    "portfolio assessment returned invalid evidence"
                )
        if row.get("truth_status_code") not in _TRUTH_STATUS_CODES:
            raise PlannerExecutionError(
                "portfolio assessment returned invalid evidence"
            )
        score = row.get("score_value")
        if isinstance(score, bool) or not isinstance(score, (int, float)):
            raise PlannerExecutionError(
                "portfolio assessment returned invalid evidence"
            )
        if isinstance(score, float) and not isfinite(score):
            raise PlannerExecutionError(
                "portfolio assessment returned invalid evidence"
            )
        if row.get("evidence_record_id") is not None:
            _parse_response_uuid(row["evidence_record_id"], "evidence record id")
        _parse_response_timestamp(row.get("valid_from"))
        if row.get("valid_to") is not None:
            _parse_response_timestamp(row["valid_to"])
        _parse_response_timestamp(row.get("recorded_at"))
        assessments.append(row)
    return {
        "architecture_object_id": str(request.architecture_object_id),
        "valid_at": request.valid_at.isoformat().replace("+00:00", "Z"),
        "recorded_at": request.recorded_at.isoformat().replace("+00:00", "Z"),
        "assessment_count": len(assessments),
        "assessments": assessments,
    }


def build_portfolio_assessment_reader(
    dsn: str | None,
    *,
    runner: CommandRunner = subprocess.run,
    base_environment: Mapping[str, str] | None = None,
):
    """Build a bounded reader without granting direct application-table SQL."""

    if not dsn:
        return _unavailable_portfolio_assessment_reader
    connection_environment = _postgres_environment(dsn, base_environment)
    if connection_environment is None:
        return _unavailable_portfolio_assessment_reader

    def reader(
        context: AuthorizationContext,
        request: PortfolioAssessmentRequest,
    ) -> Mapping[str, object]:
        """Read one bitemporal assessment collection through the SQL read port."""

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
            f"architecture_object_id={request.architecture_object_id}",
            "--set",
            f"valid_at={request.valid_at.isoformat()}",
            "--set",
            f"recorded_at={request.recorded_at.isoformat()}",
            "--set",
            f"framework_code={request.framework_code or ''}",
            "--set",
            f"cycle_code={request.cycle_code or ''}",
            "--command",
            _PORTFOLIO_ASSESSMENT_SQL,
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
                "portfolio assessment database command failed"
            ) from error
        if result.returncode != 0:
            raise PlannerExecutionError("portfolio assessment database query failed")
        try:
            response = json.loads(result.stdout.strip())
        except json.JSONDecodeError as error:
            raise PlannerExecutionError(
                "portfolio assessment returned invalid JSON"
            ) from error
        return _validate_portfolio_assessment_response(response, request)

    return reader
