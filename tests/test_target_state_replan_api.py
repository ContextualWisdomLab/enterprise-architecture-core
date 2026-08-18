"""Test-first contract for replanning after a detected target-state gap."""

from __future__ import annotations

import json
from types import SimpleNamespace
from uuid import UUID

import pytest

from ea_core_foundation.authorization import AuthorizationContext
from ea_core_foundation.replan import (
    TargetStateReplanRequest,
    build_replan_authorization_config,
    build_target_state_replan_writer,
    parse_target_state_replan_request,
)
from ea_core_foundation.service import PlannerExecutionError, PlannerRequestError

_PREDECESSOR_ID = "0196e010-1111-7111-8111-111111111191"
_REPLACEMENT_ID = "0196e110-1111-7111-8111-111111111191"
_SCENARIO_ID = "0196e120-1111-7111-8111-111111111191"
_INITIATIVE_ID = "0196e130-1111-7111-8111-111111111191"
_DECISION_REQUEST_ID = "0196e140-1111-7111-8111-111111111191"
_EVIDENCE_ID = "0195d145-64e8-7f4f-8a23-a0cc784cbf10"
_HISTORY_ID = "0196e150-1111-7111-8111-111111111191"
_REPLAN_RECORD_ID = "0196e160-1111-7111-8111-111111111191"
_OUTBOX_ID = "0196e170-1111-7111-8111-111111111191"
_PATH = f"/v1/architecture-transformations/{_PREDECESSOR_ID}/replan"


def _payload(**changes: object) -> dict[str, object]:
    """Return one valid bounded replacement-plan request with optional mutations."""

    payload: dict[str, object] = {
        "decision_request_id": _DECISION_REQUEST_ID,
        "replacement_architecture_transformation_id": _REPLACEMENT_ID,
        "architecture_scenario_id": _SCENARIO_ID,
        "remediation_initiative_id": _INITIATIVE_ID,
        "transformation_code": "database_target_state_v2",
        "transformation_title": "Replan database target state",
        "transformation_description": "Replace the gap-detected target state.",
        "effective_at": "2027-02-03T00:00:00Z",
        "decision_reason_text": (
            "Verification evidence requires a governed replacement."
        ),
        "evidence_record_id": _EVIDENCE_ID,
    }
    payload.update(changes)
    return payload


def _context() -> AuthorizationContext:
    """Return one already-verified Keyverse replanning identity."""

    return AuthorizationContext(
        tenant_record_id=UUID("018f47b2-905a-7b16-bfd4-7e4f53f10e91"),
        role_code="ea_target_state_replanner",
        subject_id="target-state-replanner-123",
        issuer_uri="https://id.example/realms/cwl",
    )


def _receipt(**changes: object) -> dict[str, object]:
    """Return one database-shaped immutable replanning receipt."""

    receipt: dict[str, object] = {
        "transformation_replan_record_id": _REPLAN_RECORD_ID,
        "predecessor_architecture_transformation_id": _PREDECESSOR_ID,
        "replacement_architecture_transformation_id": _REPLACEMENT_ID,
        "transformation_history_record_id": _HISTORY_ID,
        "outbox_event_id": _OUTBOX_ID,
        "decision_request_id": _DECISION_REQUEST_ID,
        "replan_recorded_at": "2027-02-03T00:00:01+00:00",
        "replayed": False,
        "next_action": "approve_target_state",
    }
    receipt.update(changes)
    return receipt


def test_parse_replan_binds_terminal_predecessor_to_explicit_replacement() -> None:
    """Replanning requires canonical identities and explicit replacement meaning."""

    request = parse_target_state_replan_request(_PATH, _payload())
    assert isinstance(request, TargetStateReplanRequest)
    assert str(request.predecessor_architecture_transformation_id) == _PREDECESSOR_ID
    assert str(request.replacement_architecture_transformation_id) == _REPLACEMENT_ID
    assert str(request.architecture_scenario_id) == _SCENARIO_ID
    assert str(request.remediation_initiative_id) == _INITIATIVE_ID
    assert request.transformation_code == "database_target_state_v2"

    with pytest.raises(PlannerRequestError, match="distinct"):
        parse_target_state_replan_request(
            _PATH,
            _payload(replacement_architecture_transformation_id=_PREDECESSOR_ID),
        )
    with pytest.raises(PlannerRequestError, match="only the documented fields"):
        parse_target_state_replan_request(
            _PATH,
            _payload(truth_status_code="authoritative"),
        )
    with pytest.raises(PlannerRequestError, match="replan path"):
        parse_target_state_replan_request(_PATH + "?unsafe=1", _payload())


def test_replan_authority_is_separate_and_fail_closed() -> None:
    """Read/verification authority never silently inherits replanning authority."""

    environment = {
        "EA_OIDC_ISSUER": "https://id.example/realms/cwl",
        "EA_OIDC_AUDIENCE": "enterprise-architecture-core",
        "EA_OIDC_JWKS_URL": (
            "https://id.example/realms/cwl/protocol/openid-connect/certs"
        ),
        "EA_TENANT_CLAIM": "tenant",
        "EA_ROLE_CLAIM": "role",
        "EA_READ_ROLES": "ea_reader",
        "EA_VERIFY_ROLES": "ea_target_state_verifier",
        "EA_REPLAN_ROLES": "ea_target_state_replanner",
    }
    config = build_replan_authorization_config(environment)
    assert config is not None
    assert config.allowed_roles == frozenset({"ea_target_state_replanner"})

    environment.pop("EA_REPLAN_ROLES")
    assert build_replan_authorization_config(environment) is None


def test_replan_writer_preserves_private_context_and_receipt_meaning() -> None:
    """Actor/reason stay off argv and replacement receipt meaning is bound exactly."""

    captured: dict[str, object] = {}

    def runner(command, **kwargs):
        captured["command"] = command
        captured["environment"] = kwargs["env"]
        return SimpleNamespace(returncode=0, stdout=json.dumps(_receipt()), stderr="")

    writer = build_target_state_replan_writer(
        "postgresql://ea_runtime:secret@127.0.0.1:5432/ea_core",
        runner=runner,
        base_environment={"PATH": "/usr/bin"},
    )
    result = writer(
        _context(),
        parse_target_state_replan_request(_PATH, _payload()),
    )

    command_text = " ".join(captured["command"])
    assert "target-state-replanner-123" not in command_text
    assert "Verification evidence requires" not in command_text
    environment = captured["environment"]
    assert environment["EA_REPLAN_ACTOR_REF"].endswith("#target-state-replanner-123")
    assert environment["EA_REPLAN_REASON_TEXT"].startswith("Verification evidence")
    assert result["replacement_architecture_transformation_id"] == _REPLACEMENT_ID
    assert result["next_action"] == "approve_target_state"


def test_replan_writer_fails_closed_on_unavailable_or_semantic_drift() -> None:
    """Unavailable storage and semantic drift never look successful."""

    request = parse_target_state_replan_request(_PATH, _payload())
    writer = build_target_state_replan_writer(None)
    with pytest.raises(PlannerExecutionError, match="unavailable"):
        writer(_context(), request)

    def drift_runner(command, **kwargs):
        del command, kwargs
        return SimpleNamespace(
            returncode=0,
            stdout=json.dumps(_receipt(next_action="start_transformation")),
            stderr="",
        )

    writer = build_target_state_replan_writer(
        "postgresql://ea_runtime@db.example/ea_core",
        runner=drift_runner,
    )
    with pytest.raises(PlannerExecutionError, match="invalid replan receipt"):
        writer(_context(), request)
