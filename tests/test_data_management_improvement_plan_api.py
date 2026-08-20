"""Test-first contract for turning one assessment gap into governed EA work."""

from __future__ import annotations

import json
from types import SimpleNamespace
from uuid import UUID

import pytest

from ea_core_foundation.authorization import AuthorizationContext
from ea_core_foundation.data_management_improvement_plan import (
    DataManagementImprovementPlanRequest,
    build_data_management_improvement_plan_authorization_config,
    build_data_management_improvement_plan_writer,
    parse_data_management_improvement_plan_request,
)
from ea_core_foundation.service import PlannerExecutionError, PlannerRequestError

_ASSESSMENT_ID = "0196f300-1111-7111-8111-111111111181"
_DECISION_ID = "0196f300-1111-7111-8111-111111111182"
_CAPABILITY_ID = "0196f300-1111-7111-8111-111111111183"
_ORGANIZATION_ID = "0196f300-1111-7111-8111-111111111184"
_PREREQUISITE_ID = "0196f300-1111-7111-8111-111111111185"
_DEPENDENCY_EVIDENCE_ID = "0196f300-1111-7111-8111-111111111186"
_PLAN_ID = "0196f300-1111-7111-8111-111111111187"
_INITIATIVE_ID = "0196f300-1111-7111-8111-111111111188"
_MILESTONE_ID = "0196f300-1111-7111-8111-111111111189"
_OUTBOX_ID = "0196f300-1111-7111-8111-11111111118a"
_PATH = f"/v1/data-management-assessments/{_ASSESSMENT_ID}/improvement-plans"


def _payload(**changes: object) -> dict[str, object]:
    """Return one valid bounded improvement-plan request with optional mutations."""

    payload: dict[str, object] = {
        "missing_evidence_code": "lineage_coverage",
        "decision_request_id": _DECISION_ID,
        "target_capability_object_id": _CAPABILITY_ID,
        "accountable_organization_object_id": _ORGANIZATION_ID,
        "initiative_code": "close_lineage_gap",
        "initiative_title": "Close lineage evidence gap",
        "milestone_code": "accept_lineage_evidence",
        "milestone_title": "Accept complete lineage evidence",
        "due_at": "2026-09-30T09:00:00Z",
        "funding_reference": "FIN-2026-042",
        "prerequisite_initiative_ids": [_PREREQUISITE_ID],
        "dependency_evidence_record_ids": [_DEPENDENCY_EVIDENCE_ID],
    }
    payload.update(changes)
    return payload


def _context() -> AuthorizationContext:
    """Return one already-verified Keyverse assessment-planning identity."""

    return AuthorizationContext(
        tenant_record_id=UUID("018f47b2-905a-7b16-bfd4-7e4f53f10e91"),
        role_code="ea_data_management_planner",
        subject_id="architecture-lead-123",
        issuer_uri="https://id.example/realms/cwl",
    )


def _receipt(**changes: object) -> dict[str, object]:
    """Return one database-shaped improvement-plan receipt."""

    receipt: dict[str, object] = {
        "assessment_improvement_plan_id": _PLAN_ID,
        "remediation_initiative_id": _INITIATIVE_ID,
        "initiative_milestone_id": _MILESTONE_ID,
        "outbox_event_id": _OUTBOX_ID,
        "replayed": False,
        "next_action": "review_and_authorize_improvement_initiative",
    }
    receipt.update(changes)
    return receipt


def test_parse_plan_binds_assessment_and_dependency_pairs() -> None:
    """The route owns assessment identity and paired dependencies remain explicit."""

    request = parse_data_management_improvement_plan_request(_PATH, _payload())
    assert isinstance(request, DataManagementImprovementPlanRequest)
    assert str(request.data_management_assessment_projection_id) == _ASSESSMENT_ID
    assert request.missing_evidence_code == "lineage_coverage"
    assert request.prerequisite_initiative_ids == (UUID(_PREREQUISITE_ID),)
    assert request.dependency_evidence_record_ids == (UUID(_DEPENDENCY_EVIDENCE_ID),)

    with pytest.raises(PlannerRequestError, match="only the documented fields"):
        parse_data_management_improvement_plan_request(
            _PATH,
            _payload(truth_status_code="authoritative"),
        )
    with pytest.raises(PlannerRequestError, match="aligned one-to-one"):
        parse_data_management_improvement_plan_request(
            _PATH,
            _payload(dependency_evidence_record_ids=[]),
        )
    with pytest.raises(PlannerRequestError, match="at most 32"):
        parse_data_management_improvement_plan_request(
            _PATH,
            _payload(
                prerequisite_initiative_ids=[_PREREQUISITE_ID] * 33,
                dependency_evidence_record_ids=[_DEPENDENCY_EVIDENCE_ID] * 33,
            ),
        )
    with pytest.raises(PlannerRequestError, match="local origin form"):
        parse_data_management_improvement_plan_request(
            "https://attacker.example" + _PATH,
            _payload(),
        )


def test_plan_authority_is_distinct_and_fail_closed() -> None:
    """Read and reassessment roles never inherit improvement-plan mutation authority."""

    environment = {
        "EA_OIDC_ISSUER": "https://id.example/realms/cwl",
        "EA_OIDC_AUDIENCE": "enterprise-architecture-core",
        "EA_OIDC_JWKS_URL": (
            "https://id.example/realms/cwl/protocol/openid-connect/certs"
        ),
        "EA_TENANT_CLAIM": "tenant",
        "EA_ROLE_CLAIM": "role",
        "EA_READ_ROLES": "ea_reader",
        "EA_DATA_MANAGEMENT_RECHECK_ROLES": "ea_data_management_rechecker",
        "EA_DATA_MANAGEMENT_PLAN_ROLES": "ea_data_management_planner",
    }
    config = build_data_management_improvement_plan_authorization_config(environment)
    assert config is not None
    assert config.allowed_roles == frozenset({"ea_data_management_planner"})

    environment.pop("EA_DATA_MANAGEMENT_PLAN_ROLES")
    assert build_data_management_improvement_plan_authorization_config(environment) is None


def test_plan_writer_calls_only_purpose_bound_command_and_validates_receipt() -> None:
    """The adapter invokes the tenant command port without direct table SQL."""

    captured: dict[str, object] = {}

    def runner(command, **kwargs):
        captured["command"] = command
        captured["environment"] = kwargs["env"]
        captured["timeout"] = kwargs["timeout"]
        return SimpleNamespace(
            returncode=0,
            stdout=json.dumps(_receipt()),
            stderr="",
        )

    request = parse_data_management_improvement_plan_request(_PATH, _payload())
    writer = build_data_management_improvement_plan_writer(
        "postgresql://ea_runtime:secret@127.0.0.1:5432/ea_core",
        runner=runner,
        base_environment={"PATH": "/usr/bin"},
    )
    result = writer(_context(), request)

    command_text = " ".join(captured["command"])
    assert "create_data_management_improvement_plan_for_tenant" in command_text
    assert "assessment_improvement_plan " not in command_text
    assert "architecture-lead-123" not in command_text
    assert "secret" not in command_text
    assert captured["timeout"] == 10
    assert result["assessment_improvement_plan_id"] == _PLAN_ID
    assert result["next_action"] == "review_and_authorize_improvement_initiative"


def test_plan_writer_fails_closed_on_unavailable_storage_and_bad_receipt() -> None:
    """Unavailable storage or malformed command evidence can never look successful."""

    request = parse_data_management_improvement_plan_request(_PATH, _payload())
    with pytest.raises(PlannerExecutionError, match="unavailable"):
        build_data_management_improvement_plan_writer(None)(_context(), request)

    def runner(command, **kwargs):
        del command, kwargs
        return SimpleNamespace(returncode=0, stdout=json.dumps(_receipt(replayed="false")), stderr="")

    with pytest.raises(PlannerExecutionError, match="invalid improvement-plan receipt"):
        build_data_management_improvement_plan_writer(
            "postgresql://ea_runtime@db.example/ea_core",
            runner=runner,
        )(_context(), request)
