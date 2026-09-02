"""Purpose-bound read ports for the Portfolio Assessment bounded context."""

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

from ..authorization import AuthorizationContext, KeyverseAuthorizationConfig
from ..service import (
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
_PORTFOLIO_ASSESSMENT_SUMMARY_PATH_SUFFIX = "/portfolio-assessment-summary"
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


def parse_portfolio_assessment_summary_request(
    path: str,
) -> PortfolioAssessmentRequest:
    """Bind the summary route to the same strict assessment query contract."""

    parsed = urlparse(path)
    if not parsed.path.endswith(_PORTFOLIO_ASSESSMENT_SUMMARY_PATH_SUFFIX):
        raise PlannerRequestError("portfolio assessment summary path is invalid")
    assessment_path = parsed._replace(
        path=(
            parsed.path[: -len(_PORTFOLIO_ASSESSMENT_SUMMARY_PATH_SUFFIX)]
            + _PORTFOLIO_ASSESSMENT_PATH_SUFFIX
        )
    ).geturl()
    return parse_portfolio_assessment_request(assessment_path)


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


def build_portfolio_assessment_summary_authorization_config(
    environ: Mapping[str, str],
) -> KeyverseAuthorizationConfig | None:
    """Build a separate Keyverse profile for portfolio summary reads."""

    read_environment = dict(environ)
    read_environment["EA_READ_ROLES"] = environ.get(
        "EA_PORTFOLIO_ASSESSMENT_SUMMARY_READ_ROLES",
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
        ) != request.architecture_object_id:
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


def summarize_portfolio_assessments(
    response: Mapping[str, object],
) -> Mapping[str, object]:
    """Summarize same-scale assessment facts without inventing cross-scale scores."""

    expected_response_fields = {
        "architecture_object_id",
        "valid_at",
        "recorded_at",
        "assessment_count",
        "assessments",
    }
    if set(response) != expected_response_fields:
        raise PlannerExecutionError(
            "portfolio assessment summary received invalid data"
        )
    assessments = response.get("assessments")
    if not isinstance(assessments, list):
        raise PlannerExecutionError(
            "portfolio assessment summary received invalid data"
        )

    group_fields = (
        "assessment_framework_code",
        "assessment_framework_title",
        "assessment_framework_version_label",
        "assessment_scale_code",
        "assessment_dimension_code",
        "assessment_dimension_title",
        "assessment_cycle_code",
        "assessment_cycle_title",
    )
    groups: dict[tuple[str, ...], dict[str, object]] = {}
    for row in assessments:
        if not isinstance(row, Mapping):
            raise PlannerExecutionError(
                "portfolio assessment summary received invalid data"
            )
        metadata = tuple(row.get(field) for field in group_fields)
        if not all(isinstance(value, str) and value for value in metadata):
            raise PlannerExecutionError(
                "portfolio assessment summary received invalid data"
            )
        score = row.get("score_value")
        if isinstance(score, bool) or not isinstance(score, (int, float)):
            raise PlannerExecutionError(
                "portfolio assessment summary received invalid data"
            )
        truth_status = row.get("truth_status_code")
        if truth_status not in _TRUTH_STATUS_CODES:
            raise PlannerExecutionError(
                "portfolio assessment summary received invalid data"
            )
        key = tuple(metadata)
        group = groups.setdefault(
            key,
            {
                **dict(zip(group_fields, key, strict=True)),
                "assessment_count": 0,
                "truth_status_codes": set(),
                "evidence_record_count": 0,
                "score_values": [],
                "score_labels": set(),
            },
        )
        group["assessment_count"] = int(group["assessment_count"]) + 1
        group["truth_status_codes"].add(truth_status)
        group["score_values"].append(score)
        score_label = row.get("score_label")
        if not isinstance(score_label, str) or not score_label:
            raise PlannerExecutionError(
                "portfolio assessment summary received invalid data"
            )
        group["score_labels"].add(score_label)
        if row.get("evidence_record_id") is not None:
            group["evidence_record_count"] = (
                int(group["evidence_record_count"]) + 1
            )

    summarized_groups: list[dict[str, object]] = []
    for key in sorted(groups):
        group = groups[key]
        statuses = group["truth_status_codes"]
        scores = group["score_values"]
        labels = group["score_labels"]
        if group["evidence_record_count"] < group["assessment_count"]:
            state = "evidence_gap"
            action = "collect_assessment_evidence"
        elif statuses & {"inferred", "proposed"}:
            state = "review_required"
            action = "review_assessment_truth"
        else:
            state = "evidence_complete"
            action = "use_assessment_evidence"
        summarized_groups.append(
            {
                **{field: group[field] for field in group_fields},
                "assessment_count": group["assessment_count"],
                "truth_status_codes": sorted(statuses),
                "evidence_record_count": group["evidence_record_count"],
                "score_value_min": min(scores),
                "score_value_max": max(scores),
                "score_labels": sorted(labels),
                "assessment_state_code": state,
                "next_action": action,
            }
        )

    if not summarized_groups:
        overall_state = "no_assessments"
        overall_action = "collect_portfolio_assessments"
    elif any(
        group["assessment_state_code"] == "evidence_gap"
        for group in summarized_groups
    ):
        overall_state = "evidence_gap"
        overall_action = "collect_assessment_evidence"
    elif any(
        group["assessment_state_code"] == "review_required"
        for group in summarized_groups
    ):
        overall_state = "review_required"
        overall_action = "review_assessment_truth"
    else:
        overall_state = "evidence_complete"
        overall_action = "use_assessment_evidence"
    return {
        "architecture_object_id": response["architecture_object_id"],
        "valid_at": response["valid_at"],
        "recorded_at": response["recorded_at"],
        "assessment_count": len(assessments),
        "group_count": len(summarized_groups),
        "assessment_state_code": overall_state,
        "next_action": overall_action,
        "groups": summarized_groups,
    }


def _render_portfolio_assessment_sql(
    context: AuthorizationContext,
    request: PortfolioAssessmentRequest,
) -> str:
    """Render validated query values for psql's non-interactive command mode."""

    query = _PORTFOLIO_ASSESSMENT_SQL
    values = (
        ("tenant_record_id", context.tenant_record_id),
        ("architecture_object_id", request.architecture_object_id),
        ("valid_at", request.valid_at.isoformat()),
        ("recorded_at", request.recorded_at.isoformat()),
        ("framework_code", request.framework_code or ""),
        ("cycle_code", request.cycle_code or ""),
    )
    for name, value in values:
        literal = "'" + str(value).replace("'", "''") + "'"
        query = query.replace(f":'{name}'", literal)
    return query


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
            "--set=ON_ERROR_STOP=1",
            "--command",
            _render_portfolio_assessment_sql(context, request),
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


def build_portfolio_assessment_summary_reader(
    dsn: str | None,
    *,
    runner: CommandRunner = subprocess.run,
    base_environment: Mapping[str, str] | None = None,
):
    """Build a summary reader that reuses the validated assessment read port."""

    assessment_reader = build_portfolio_assessment_reader(
        dsn,
        runner=runner,
        base_environment=base_environment,
    )

    def reader(
        context: AuthorizationContext,
        request: PortfolioAssessmentRequest,
    ) -> Mapping[str, object]:
        """Summarize one validated assessment collection for a buyer."""

        return summarize_portfolio_assessments(assessment_reader(context, request))

    return reader
