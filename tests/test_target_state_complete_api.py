"""Test-first contract for completing a started EA transformation."""

from __future__ import annotations

import json
import subprocess
from types import SimpleNamespace
from uuid import UUID

import pytest

from ea_core_foundation.authorization import AuthorizationContext
from ea_core_foundation.complete import (
    TargetStateCompleteRequest,
    build_complete_authorization_config,
    build_target_state_complete_writer,
    parse_target_state_complete_request,
)
from ea_core_foundation.service import PlannerExecutionError, PlannerRequestError

_TRANSFORMATION_ID = "0196e010-1111-7111-8111-111111111191"
_DECISION_REQUEST_ID = "0196e090-1111-7111-8111-111111111193"
_EVIDENCE_ID = "0195d145-64e8-7f4f-8a23-a0cc784cbf10"
_HISTORY_ID = "0196e091-1111-7111-8111-111111111193"
_OUTBOX_ID = "0196e092-1111-7111-8111-111111111193"
_PATH = f"/v1/architecture-transformations/{_TRANSFORMATION_ID}/complete"


def _payload(**changes: object) -> dict[str, object]:
    """Return one valid completion command with optional mutations."""

    payload: dict[str, object] = {
        "decision_request_id": _DECISION_REQUEST_ID,
        "effective_at": "2027-02-01T00:00:00Z",
        "decision_reason_text": (
            "Confirm the governed target-state execution is complete."
        ),
        "evidence_record_id": _EVIDENCE_ID,
    }
    payload.update(changes)
    return payload


def _context() -> AuthorizationContext:
    """Return one already-verified Keyverse authorization context."""

    return AuthorizationContext(
        tenant_record_id=UUID("018f47b2-905a-7b16-bfd4-7e4f53f10e91"),
        role_code="ea_transformation_completer",
        subject_id="transformation-verifier-123",
        issuer_uri="https://id.example/realms/cwl",
    )


def _receipt(**changes: object) -> dict[str, object]:
    """Return one valid immutable completion receipt."""

    receipt: dict[str, object] = {
        "transformation_history_record_id": _HISTORY_ID,
        "architecture_transformation_id": _TRANSFORMATION_ID,
        "transformation_state_code": "completed",
        "outbox_event_id": _OUTBOX_ID,
        "decision_request_id": _DECISION_REQUEST_ID,
        "completion_recorded_at": "2027-02-01T00:00:01+00:00",
        "replayed": False,
        "next_action": "verify_target_state",
    }
    receipt.update(changes)
    return receipt


def test_parse_completion_binds_path_and_strict_body() -> None:
    """Completion accepts only one canonical transformation and documented JSON."""

    request = parse_target_state_complete_request(_PATH, _payload())
    assert isinstance(request, TargetStateCompleteRequest)
    assert str(request.architecture_transformation_id) == _TRANSFORMATION_ID
    assert str(request.decision_request_id) == _DECISION_REQUEST_ID
    assert str(request.evidence_record_id) == _EVIDENCE_ID
    assert request.decision_reason_text.startswith("Confirm")

    with pytest.raises(PlannerRequestError, match="only the documented fields"):
        parse_target_state_complete_request(
            _PATH,
            _payload(decision_actor_ref="spoofed"),
        )
    with pytest.raises(PlannerRequestError, match="completion path"):
        parse_target_state_complete_request(_PATH + "?unsafe=1", _payload())


def test_completion_authority_is_separate_from_read_or_start_roles() -> None:
    """Deployments must configure an explicit Keyverse completion role boundary."""

    environment = {
        "EA_OIDC_ISSUER": "https://id.example/realms/cwl",
        "EA_OIDC_AUDIENCE": "enterprise-architecture-core",
        "EA_OIDC_JWKS_URL": (
            "https://id.example/realms/cwl/protocol/openid-connect/certs"
        ),
        "EA_TENANT_CLAIM": "tenant",
        "EA_ROLE_CLAIM": "role",
        "EA_READ_ROLES": "ea_reader",
        "EA_COMPLETE_ROLES": "ea_transformation_completer",
    }
    config = build_complete_authorization_config(environment)
    assert config is not None
    assert config.allowed_roles == frozenset({"ea_transformation_completer"})


def test_completion_writer_preserves_private_decision_context() -> None:
    """Actor/reason avoid argv while the exact immutable receipt is verified."""

    captured: dict[str, object] = {}

    def runner(command, **kwargs):
        captured["command"] = command
        captured["environment"] = kwargs["env"]
        return SimpleNamespace(returncode=0, stdout=json.dumps(_receipt()), stderr="")

    writer = build_target_state_complete_writer(
        "postgresql://ea_runtime:secret@127.0.0.1:5432/ea_core",
        runner=runner,
        base_environment={"PATH": "/usr/bin"},
    )
    result = writer(
        _context(),
        parse_target_state_complete_request(_PATH, _payload()),
    )

    command_text = " ".join(captured["command"])
    assert "transformation-verifier-123" not in command_text
    assert "Confirm the governed" not in command_text
    environment = captured["environment"]
    assert environment["EA_COMPLETE_ACTOR_REF"].endswith(
        "#transformation-verifier-123"
    )
    assert environment["EA_COMPLETE_REASON_TEXT"].startswith("Confirm")
    assert result["transformation_state_code"] == "completed"
    assert result["next_action"] == "verify_target_state"


def test_completion_writer_fails_closed_on_receipt_drift_or_database_failure() -> None:
    """A malformed or failed completion command can never look successful."""

    def malformed_runner(command, **kwargs):
        del command, kwargs
        return SimpleNamespace(
            returncode=0,
            stdout=json.dumps(_receipt(next_action="done")),
            stderr="",
        )

    writer = build_target_state_complete_writer(
        "postgresql://ea_runtime:secret@127.0.0.1:5432/ea_core",
        runner=malformed_runner,
    )
    with pytest.raises(PlannerExecutionError, match="invalid completion receipt"):
        writer(_context(), parse_target_state_complete_request(_PATH, _payload()))

    def timeout_runner(command, **kwargs):
        del command, kwargs
        raise subprocess.TimeoutExpired("psql", 10)

    writer = build_target_state_complete_writer(
        "postgresql://ea_runtime:secret@127.0.0.1:5432/ea_core",
        runner=timeout_runner,
    )
    with pytest.raises(PlannerExecutionError, match="database command failed"):
        writer(_context(), parse_target_state_complete_request(_PATH, _payload()))
