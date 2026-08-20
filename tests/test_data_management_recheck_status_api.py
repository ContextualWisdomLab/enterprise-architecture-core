"""Test-first contract for following an evidence-backed assessment recheck."""

from __future__ import annotations

import json
import subprocess
from types import SimpleNamespace
from uuid import UUID

import pytest

from ea_core_foundation.authorization import AuthorizationContext
from ea_core_foundation.data_management_recheck_status import (
    DataManagementRecheckStatusRequest,
    build_data_management_recheck_status_authorization_config,
    build_data_management_recheck_status_reader,
    parse_data_management_recheck_status_request,
)
from ea_core_foundation.service import PlannerExecutionError, PlannerRequestError

_RECHECK_ID = "0196f300-1111-7111-8111-111111111174"
_ASSESSMENT_ID = "0196f300-1111-7111-8111-111111111171"
_SUCCESSOR_ID = "0196f300-1111-7111-8111-111111111181"
_PATH = f"/v1/data-management-assessment-rechecks/{_RECHECK_ID}"


def _context() -> AuthorizationContext:
    """Return one already-verified Keyverse reassessment-status reader."""

    return AuthorizationContext(
        tenant_record_id=UUID("018f47b2-905a-7b16-bfd4-7e4f53f10e91"),
        role_code="ea_data_management_recheck_reader",
        subject_id="data-governance-lead-123",
        issuer_uri="https://id.example/realms/cwl",
    )


def _payload(**changes: object) -> dict[str, object]:
    """Return one database-shaped reassessment status with remaining evidence gaps."""

    payload: dict[str, object] = {
        "assessment_recheck_request_id": _RECHECK_ID,
        "data_management_assessment_projection_id": _ASSESSMENT_ID,
        "successor_assessment_projection_id": _SUCCESSOR_ID,
        "successor_truth_status_code": "observed",
        "recheck_state_code": "evidence_gap",
        "successor_readiness_code": "evidence_gap",
        "successor_overall_score_basis_points": 7200,
        "successor_missing_evidence_count": 2,
        "next_action": "plan_remaining_assessment_gap",
    }
    payload.update(changes)
    return payload


def _runner_with_stdout(stdout: str):
    """Return one deterministic successful subprocess adapter."""

    def runner(command, **kwargs):
        del command, kwargs
        return SimpleNamespace(returncode=0, stdout=stdout, stderr="")

    return runner


def test_parse_recheck_status_binds_one_canonical_request_identity() -> None:
    """The status route accepts only one local-origin canonical UUIDv7 resource."""

    request = parse_data_management_recheck_status_request(_PATH)
    assert isinstance(request, DataManagementRecheckStatusRequest)
    assert str(request.assessment_recheck_request_id) == _RECHECK_ID

    for invalid_path in (
        _PATH + "?unsafe=1",
        "https://attacker.example" + _PATH,
        "//attacker.example" + _PATH,
        "/v1/data-management-assessment-rechecks/not-a-uuid",
        _PATH + "/nested",
        "/v1/not-a-recheck-status",
    ):
        with pytest.raises(PlannerRequestError):
            parse_data_management_recheck_status_request(invalid_path)


def test_recheck_status_authority_is_distinct_and_fail_closed() -> None:
    """Mutation authority does not silently grant reassessment-status reads."""

    environment = {
        "EA_OIDC_ISSUER": "https://id.example/realms/cwl",
        "EA_OIDC_AUDIENCE": "enterprise-architecture-core",
        "EA_OIDC_JWKS_URL": (
            "https://id.example/realms/cwl/protocol/openid-connect/certs"
        ),
        "EA_TENANT_CLAIM": "tenant",
        "EA_ROLE_CLAIM": "role",
        "EA_DATA_MANAGEMENT_RECHECK_ROLES": "ea_data_management_rechecker",
        "EA_DATA_MANAGEMENT_RECHECK_READ_ROLES": "ea_data_management_recheck_reader",
    }
    config = build_data_management_recheck_status_authorization_config(environment)
    assert config is not None
    assert config.allowed_roles == frozenset({"ea_data_management_recheck_reader"})

    environment.pop("EA_DATA_MANAGEMENT_RECHECK_READ_ROLES")
    assert (
        build_data_management_recheck_status_authorization_config(environment) is None
    )


def test_recheck_status_reader_uses_purpose_bound_port_and_validates_meaning() -> None:
    """The adapter executes only the status port and rejects semantic drift."""

    captured: dict[str, object] = {}

    def runner(command, **kwargs):
        captured["command"] = command
        captured["environment"] = kwargs["env"]
        captured["timeout"] = kwargs["timeout"]
        return SimpleNamespace(
            returncode=0,
            stdout=json.dumps(_payload()),
            stderr="",
        )

    reader = build_data_management_recheck_status_reader(
        "postgresql://ea_runtime:secret@127.0.0.1:5432/ea_core",
        runner=runner,
        base_environment={"PATH": "/usr/bin"},
    )
    result = reader(_context(), parse_data_management_recheck_status_request(_PATH))

    command_text = " ".join(captured["command"])
    assert "read_data_management_assessment_recheck_status" in command_text
    assert "assessment_recheck_request " not in command_text
    assert "data-governance-lead-123" not in command_text
    assert "secret" not in command_text
    assert captured["timeout"] == 10
    assert result["successor_truth_status_code"] == "observed"
    assert result["recheck_state_code"] == "evidence_gap"
    assert result["next_action"] == "plan_remaining_assessment_gap"


def test_recheck_status_reader_accepts_waiting_and_complete_states() -> None:
    """Buyer actions distinguish waiting, remaining gaps, and evidence completion."""

    cases = (
        (
            {
                "assessment_recheck_request_id": _RECHECK_ID,
                "data_management_assessment_projection_id": _ASSESSMENT_ID,
                "successor_assessment_projection_id": None,
                "successor_truth_status_code": None,
                "recheck_state_code": "awaiting_result",
                "successor_readiness_code": None,
                "successor_overall_score_basis_points": None,
                "successor_missing_evidence_count": None,
                "next_action": "await_assessment_recheck",
            },
            "await_assessment_recheck",
        ),
        (
            _payload(
                recheck_state_code="evidence_complete",
                successor_readiness_code="evidence_complete",
                successor_overall_score_basis_points=10000,
                successor_missing_evidence_count=0,
                next_action="close_assessment_improvement_loop",
            ),
            "close_assessment_improvement_loop",
        ),
    )
    request = parse_data_management_recheck_status_request(_PATH)
    for payload, expected_action in cases:
        reader = build_data_management_recheck_status_reader(
            "postgresql://ea_runtime@db.example/ea_core",
            runner=_runner_with_stdout(json.dumps(payload)),
        )
        assert reader(_context(), request)["next_action"] == expected_action


def test_recheck_status_reader_fails_closed_when_storage_is_unavailable() -> None:
    """Missing and non-PostgreSQL storage configuration cannot create fake status."""

    request = parse_data_management_recheck_status_request(_PATH)
    for dsn in (None, "https://db.example/ea_core"):
        with pytest.raises(PlannerExecutionError, match="unavailable"):
            build_data_management_recheck_status_reader(dsn)(_context(), request)


def test_recheck_status_reader_fails_closed_on_transport_errors() -> None:
    """Process failures, missing psql, and timeouts remain non-successful reads."""

    request = parse_data_management_recheck_status_request(_PATH)

    def failed_runner(command, **kwargs):
        del command, kwargs
        return SimpleNamespace(returncode=1, stdout="", stderr="boom")

    with pytest.raises(PlannerExecutionError, match="query failed"):
        build_data_management_recheck_status_reader(
            "postgresql://ea_runtime@db.example/ea_core",
            runner=failed_runner,
        )(_context(), request)

    def unavailable_runner(command, **kwargs):
        del command, kwargs
        raise OSError("psql unavailable")

    with pytest.raises(PlannerExecutionError, match="command failed"):
        build_data_management_recheck_status_reader(
            "postgresql://ea_runtime@db.example/ea_core",
            runner=unavailable_runner,
        )(_context(), request)

    def timeout_runner(command, **kwargs):
        del kwargs
        raise subprocess.TimeoutExpired(command, 10)

    with pytest.raises(PlannerExecutionError, match="command failed"):
        build_data_management_recheck_status_reader(
            "postgresql://ea_runtime@db.example/ea_core",
            runner=timeout_runner,
        )(_context(), request)


def test_recheck_status_reader_rejects_invalid_storage_evidence() -> None:
    """Malformed JSON, IDs, truth, and state drift fail closed."""

    request = parse_data_management_recheck_status_request(_PATH)
    invalid_payloads = (
        "not-json",
        json.dumps([]),
        json.dumps(_payload(extra_field="unsafe")),
        json.dumps(_payload(assessment_recheck_request_id=_SUCCESSOR_ID)),
        json.dumps(_payload(data_management_assessment_projection_id=1)),
        json.dumps(_payload(successor_assessment_projection_id="not-a-uuid")),
        json.dumps(_payload(successor_assessment_projection_id=None)),
        json.dumps(_payload(successor_truth_status_code="unknown")),
        json.dumps(_payload(successor_truth_status_code=[])),
        json.dumps(_payload(successor_readiness_code=[])),
        json.dumps(_payload(successor_overall_score_basis_points=True)),
        json.dumps(_payload(successor_overall_score_basis_points=10001)),
        json.dumps(_payload(successor_missing_evidence_count=True)),
        json.dumps(_payload(successor_missing_evidence_count=-1)),
        json.dumps(_payload(recheck_state_code="unknown")),
        json.dumps(_payload(next_action="approve_without_evidence")),
        json.dumps(_payload(successor_missing_evidence_count=0)),
        json.dumps(_payload(successor_truth_status_code="proposed")),
        json.dumps(
            _payload(
                successor_truth_status_code="observed",
                recheck_state_code="review_required",
                next_action="review_assessment_recheck_evidence",
            )
        ),
        json.dumps(
            {
                "assessment_recheck_request_id": _RECHECK_ID,
                "data_management_assessment_projection_id": _ASSESSMENT_ID,
                "successor_assessment_projection_id": _SUCCESSOR_ID,
                "successor_truth_status_code": None,
                "recheck_state_code": "awaiting_result",
                "successor_readiness_code": None,
                "successor_overall_score_basis_points": None,
                "successor_missing_evidence_count": None,
                "next_action": "await_assessment_recheck",
            }
        ),
        json.dumps(
            {
                "assessment_recheck_request_id": _RECHECK_ID,
                "data_management_assessment_projection_id": _ASSESSMENT_ID,
                "successor_assessment_projection_id": None,
                "successor_truth_status_code": None,
                "recheck_state_code": "awaiting_result",
                "successor_readiness_code": None,
                "successor_overall_score_basis_points": None,
                "successor_missing_evidence_count": None,
                "next_action": "retry_assessment_recheck",
            }
        ),
        json.dumps(
            _payload(
                recheck_state_code="evidence_complete",
                successor_readiness_code="evidence_complete",
                successor_missing_evidence_count=1,
                next_action="close_assessment_improvement_loop",
            )
        ),
    )
    for stdout in invalid_payloads:
        reader = build_data_management_recheck_status_reader(
            "postgresql://ea_runtime@db.example/ea_core",
            runner=_runner_with_stdout(stdout),
        )
        with pytest.raises(PlannerExecutionError):
            reader(_context(), request)
