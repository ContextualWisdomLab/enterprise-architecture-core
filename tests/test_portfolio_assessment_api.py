"""Test-first contract for the authenticated portfolio assessment read port."""

from __future__ import annotations

import json
import subprocess
from types import SimpleNamespace
from uuid import UUID

import pytest

from ea_core_foundation.authorization import AuthorizationContext
from ea_core_foundation.portfolio import (
    PortfolioAssessmentRequest,
    build_portfolio_assessment_authorization_config,
    build_portfolio_assessment_reader,
    parse_portfolio_assessment_request,
)
from ea_core_foundation.service import PlannerExecutionError, PlannerRequestError

_OBJECT_ID = "0196f300-1111-7111-8111-111111111174"
_EVIDENCE_ID = "0196f300-1111-7111-8111-111111111181"
_PATH = (
    f"/v1/architecture-objects/{_OBJECT_ID}/portfolio-assessments"
    "?valid_at=2026-08-20T00%3A00%3A00Z"
    "&recorded_at=2026-08-20T01%3A00%3A00Z"
    "&framework_code=application_fitness"
    "&cycle_code=annual_review"
)
_MINIMAL_PATH = (
    f"/v1/architecture-objects/{_OBJECT_ID}/portfolio-assessments"
    "?valid_at=2026-08-20T00%3A00%3A00Z"
    "&recorded_at=2026-08-20T01%3A00%3A00Z"
)


def _context() -> AuthorizationContext:
    """Return one already-verified portfolio assessment reader context."""

    return AuthorizationContext(
        tenant_record_id=UUID("018f47b2-905a-7b16-bfd4-7e4f53f10e91"),
        role_code="ea_portfolio_assessment_reader",
        subject_id="portfolio-reviewer-123",
        issuer_uri="https://id.example/realms/cwl",
    )


def _row(**changes: object) -> dict[str, object]:
    """Return one database-shaped portfolio assessment fact."""

    result: dict[str, object] = {
        "architecture_object_id": _OBJECT_ID,
        "assessment_framework_code": "application_fitness",
        "assessment_framework_title": "Application Fitness",
        "assessment_framework_version_label": "2026.1",
        "assessment_scale_code": "score_scale",
        "assessment_dimension_code": "business_fit",
        "assessment_dimension_title": "Business Fit",
        "assessment_cycle_code": "annual_review",
        "assessment_cycle_title": "Annual Review",
        "score_value": 3.0,
        "score_label": "Watch",
        "truth_status_code": "observed",
        "evidence_record_id": _EVIDENCE_ID,
        "valid_from": "2026-01-01T00:00:00+00:00",
        "valid_to": None,
        "recorded_at": "2026-08-20T00:30:00+00:00",
    }
    result.update(changes)
    return result


def _runner_with_stdout(stdout: str):
    """Return one deterministic successful subprocess adapter."""

    def runner(command, **kwargs):
        del command, kwargs
        return SimpleNamespace(returncode=0, stdout=stdout, stderr="")

    return runner


def test_parse_portfolio_assessment_binds_cutoffs_and_selectors() -> None:
    """The read route accepts only canonical identity, cutoff, and bounded selectors."""

    request = parse_portfolio_assessment_request(_PATH)
    assert isinstance(request, PortfolioAssessmentRequest)
    assert str(request.architecture_object_id) == _OBJECT_ID
    assert request.framework_code == "application_fitness"
    assert request.cycle_code == "annual_review"

    invalid_paths = (
        _PATH + "&framework_code=application_fitness",
        _PATH.replace("&cycle_code=annual_review", "&unknown=value"),
        _MINIMAL_PATH + "&framework_code=x",
        _MINIMAL_PATH + "&cycle_code=bad-code",
        _MINIMAL_PATH.split("&recorded_at", 1)[0],
        _PATH.replace(_OBJECT_ID, "not-a-uuid"),
        "https://attacker.example" + _PATH,
        "//attacker.example" + _PATH,
        _PATH + "#fragment",
        _PATH.replace("/portfolio-assessments", "/portfolio-assessments/nested"),
        _MINIMAL_PATH.replace(
            "/portfolio-assessments", "//portfolio-assessments"
        ),
    )
    for invalid_path in invalid_paths:
        with pytest.raises(PlannerRequestError):
            parse_portfolio_assessment_request(invalid_path)


def test_portfolio_assessment_authority_is_dedicated_and_fail_closed() -> None:
    """The portfolio read role is not inherited from mutation or generic reads."""

    environment = {
        "EA_OIDC_ISSUER": "https://id.example/realms/cwl",
        "EA_OIDC_AUDIENCE": "enterprise-architecture-core",
        "EA_OIDC_JWKS_URL": (
            "https://id.example/realms/cwl/protocol/openid-connect/certs"
        ),
        "EA_TENANT_CLAIM": "tenant",
        "EA_ROLE_CLAIM": "role",
        "EA_READ_ROLES": "ea_reader",
        "EA_PORTFOLIO_ASSESSMENT_READ_ROLES": "ea_portfolio_assessment_reader",
    }
    config = build_portfolio_assessment_authorization_config(environment)
    assert config is not None
    assert config.allowed_roles == frozenset({"ea_portfolio_assessment_reader"})

    environment.pop("EA_PORTFOLIO_ASSESSMENT_READ_ROLES")
    assert build_portfolio_assessment_authorization_config(environment) is None


def test_portfolio_assessment_reader_uses_only_the_purpose_bound_sql_port() -> None:
    """The adapter never places direct-table SQL, credentials, or PII in its command."""

    captured: dict[str, object] = {}

    def runner(command, **kwargs):
        captured["command"] = command
        captured["environment"] = kwargs["env"]
        captured["timeout"] = kwargs["timeout"]
        return SimpleNamespace(
            returncode=0,
            stdout=json.dumps([_row()]),
            stderr="",
        )

    reader = build_portfolio_assessment_reader(
        "postgresql://ea_runtime:secret@127.0.0.1:5432/ea_core",
        runner=runner,
        base_environment={"PATH": "/usr/bin"},
    )
    result = reader(_context(), parse_portfolio_assessment_request(_PATH))

    command_text = " ".join(captured["command"])
    assert "read_portfolio_assessment_for_tenant" in command_text
    assert "object_assessment " not in command_text
    assert "portfolio-reviewer-123" not in command_text
    assert "secret" not in command_text
    assert captured["timeout"] == 10
    assert result["assessment_count"] == 1
    assert result["assessments"][0]["truth_status_code"] == "observed"


def test_portfolio_assessment_reader_accepts_empty_results() -> None:
    """A valid object with no visible facts is an explicit empty collection."""

    reader = build_portfolio_assessment_reader(
        "postgresql://ea_runtime@db.example/ea_core",
        runner=_runner_with_stdout("[]"),
    )
    result = reader(_context(), parse_portfolio_assessment_request(_PATH))
    assert result["assessment_count"] == 0
    assert result["assessments"] == []


def test_portfolio_assessment_reader_accepts_review_evidence_without_evidence_id(
) -> None:
    """An inferred fact may remain reviewable before evidence is attached."""

    reader = build_portfolio_assessment_reader(
        "postgresql://ea_runtime@db.example/ea_core",
        runner=_runner_with_stdout(
            json.dumps([_row(truth_status_code="inferred", evidence_record_id=None)])
        ),
    )
    result = reader(_context(), parse_portfolio_assessment_request(_PATH))
    assert result["assessments"][0]["evidence_record_id"] is None


def test_portfolio_assessment_reader_fails_closed_without_storage() -> None:
    """Missing or non-PostgreSQL storage cannot create a synthetic assessment."""

    request = parse_portfolio_assessment_request(_PATH)
    for dsn in (None, "https://db.example/ea_core"):
        with pytest.raises(PlannerExecutionError, match="unavailable"):
            build_portfolio_assessment_reader(dsn)(_context(), request)


def test_portfolio_assessment_reader_fails_closed_on_transport_errors() -> None:
    """Process failure, missing psql, and timeout remain retriable non-successes."""

    request = parse_portfolio_assessment_request(_PATH)

    def failed_runner(command, **kwargs):
        del command, kwargs
        return SimpleNamespace(returncode=1, stdout="", stderr="boom")

    with pytest.raises(PlannerExecutionError, match="query failed"):
        build_portfolio_assessment_reader(
            "postgresql://ea_runtime@db.example/ea_core",
            runner=failed_runner,
        )(_context(), request)

    def unavailable_runner(command, **kwargs):
        del command, kwargs
        raise OSError("psql unavailable")

    with pytest.raises(PlannerExecutionError, match="command failed"):
        build_portfolio_assessment_reader(
            "postgresql://ea_runtime@db.example/ea_core",
            runner=unavailable_runner,
        )(_context(), request)

    def timeout_runner(command, **kwargs):
        del kwargs
        raise subprocess.TimeoutExpired(command, 10)

    with pytest.raises(PlannerExecutionError, match="command failed"):
        build_portfolio_assessment_reader(
            "postgresql://ea_runtime@db.example/ea_core",
            runner=timeout_runner,
        )(_context(), request)


@pytest.mark.parametrize(
    "stdout",
    [
        "not-json",
        json.dumps({}),
        json.dumps([{}]),
        json.dumps([_row(architecture_object_id="0196f300-1111-7111-8111-111111111181")]),
        json.dumps([_row(architecture_object_id=None)]),
        json.dumps([_row(truth_status_code="rejected")]),
        json.dumps([_row(score_value=True)]),
        json.dumps([_row(score_value=float("inf"))]),
        json.dumps([_row(score_label="")]),
        json.dumps([_row(evidence_record_id="not-a-uuid")]),
        json.dumps([_row(valid_from="not-a-time")]),
        json.dumps([_row(valid_from=None)]),
        json.dumps([_row(valid_to="not-a-time")]),
        json.dumps([_row(recorded_at="2026-08-20T00:00:00")]),
    ],
)
def test_portfolio_assessment_reader_rejects_invalid_storage_evidence(
    stdout: str,
) -> None:
    """Malformed, expanded, cross-object, or untrusted evidence never reaches buyers."""

    with pytest.raises(PlannerExecutionError):
        build_portfolio_assessment_reader(
            "postgresql://ea_runtime@db.example/ea_core",
            runner=_runner_with_stdout(stdout),
        )(_context(), parse_portfolio_assessment_request(_PATH))
