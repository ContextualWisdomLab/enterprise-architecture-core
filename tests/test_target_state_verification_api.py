"""Test-first contract for verifying a completed EA target state."""

from __future__ import annotations

import json
import subprocess
from types import SimpleNamespace
from uuid import UUID

import pytest

from ea_core_foundation.authorization import AuthorizationContext
from ea_core_foundation.service import PlannerExecutionError, PlannerRequestError
from ea_core_foundation.verify import (
    TargetStateVerificationRequest,
    build_target_state_verification_writer,
    build_verification_authorization_config,
    parse_target_state_verification_request,
)

_TRANSFORMATION_ID = "0196e010-1111-7111-8111-111111111191"
_DECISION_REQUEST_ID = "0196e0a0-1111-7111-8111-111111111193"
_EVIDENCE_ID = "0195d145-64e8-7f4f-8a23-a0cc784cbf10"
_HISTORY_ID = "0196e0a1-1111-7111-8111-111111111193"
_OUTBOX_ID = "0196e0a2-1111-7111-8111-111111111193"
_PATH = f"/v1/architecture-transformations/{_TRANSFORMATION_ID}/verification"


def _payload(**changes: object) -> dict[str, object]:
    """Return one valid verification request body with optional mutations."""

    payload: dict[str, object] = {
        "decision_request_id": _DECISION_REQUEST_ID,
        "effective_at": "2027-02-02T00:00:00Z",
        "decision_reason_text": "Evidence confirms the approved target state.",
        "evidence_record_id": _EVIDENCE_ID,
        "verification_outcome_code": "verified",
    }
    payload.update(changes)
    return payload


def _context() -> AuthorizationContext:
    """Return one already-verified Keyverse verification identity."""

    return AuthorizationContext(
        tenant_record_id=UUID("018f47b2-905a-7b16-bfd4-7e4f53f10e91"),
        role_code="ea_target_state_verifier",
        subject_id="target-state-verifier-123",
        issuer_uri="https://id.example/realms/cwl",
    )


def _receipt(**changes: object) -> dict[str, object]:
    """Return one database-shaped immutable verification receipt."""

    receipt: dict[str, object] = {
        "transformation_history_record_id": _HISTORY_ID,
        "architecture_transformation_id": _TRANSFORMATION_ID,
        "verification_outcome_code": "verified",
        "outbox_event_id": _OUTBOX_ID,
        "decision_request_id": _DECISION_REQUEST_ID,
        "verification_recorded_at": "2027-02-02T00:00:01+00:00",
        "replayed": False,
        "next_action": "monitor_target_state",
    }
    receipt.update(changes)
    return receipt


def test_parse_verification_binds_path_body_and_outcome() -> None:
    """Verification accepts only canonical route identity and explicit outcome."""

    request = parse_target_state_verification_request(_PATH, _payload())
    assert isinstance(request, TargetStateVerificationRequest)
    assert str(request.architecture_transformation_id) == _TRANSFORMATION_ID
    assert str(request.decision_request_id) == _DECISION_REQUEST_ID
    assert str(request.evidence_record_id) == _EVIDENCE_ID
    assert request.verification_outcome_code == "verified"

    gap = parse_target_state_verification_request(
        _PATH,
        _payload(verification_outcome_code="gap_detected"),
    )
    assert gap.verification_outcome_code == "gap_detected"

    with pytest.raises(PlannerRequestError, match="verification outcome"):
        parse_target_state_verification_request(
            _PATH,
            _payload(verification_outcome_code="auto_approved"),
        )
    with pytest.raises(PlannerRequestError, match="only the documented fields"):
        parse_target_state_verification_request(
            _PATH,
            _payload(decision_actor_ref="spoofed"),
        )
    with pytest.raises(PlannerRequestError, match="verification path"):
        parse_target_state_verification_request(_PATH + "?unsafe=1", _payload())


def test_verification_authority_is_separate_and_fail_closed() -> None:
    """Read/completion authority never silently inherits verification authority."""

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
        "EA_VERIFY_ROLES": "ea_target_state_verifier",
    }
    config = build_verification_authorization_config(environment)
    assert config is not None
    assert config.allowed_roles == frozenset({"ea_target_state_verifier"})

    environment.pop("EA_VERIFY_ROLES")
    assert build_verification_authorization_config(environment) is None


def test_verification_writer_preserves_private_context_and_receipt_meaning() -> None:
    """Actor/reason stay off argv and verified receipt meaning is bound exactly."""

    captured: dict[str, object] = {}

    def runner(command, **kwargs):
        captured["command"] = command
        captured["environment"] = kwargs["env"]
        return SimpleNamespace(returncode=0, stdout=json.dumps(_receipt()), stderr="")

    writer = build_target_state_verification_writer(
        "postgresql://ea_runtime:secret@127.0.0.1:5432/ea_core",
        runner=runner,
        base_environment={"PATH": "/usr/bin"},
    )
    result = writer(
        _context(),
        parse_target_state_verification_request(_PATH, _payload()),
    )

    command_text = " ".join(captured["command"])
    assert "target-state-verifier-123" not in command_text
    assert "Evidence confirms" not in command_text
    environment = captured["environment"]
    assert environment["EA_VERIFY_ACTOR_REF"].endswith("#target-state-verifier-123")
    assert environment["EA_VERIFY_REASON_TEXT"].startswith("Evidence confirms")
    assert result["verification_outcome_code"] == "verified"
    assert result["next_action"] == "monitor_target_state"


def test_verification_writer_gap_receipt_has_replan_action() -> None:
    """A detected gap must route the buyer to replanning, never monitoring."""

    request = parse_target_state_verification_request(
        _PATH,
        _payload(verification_outcome_code="gap_detected"),
    )

    def runner(command, **kwargs):
        del command, kwargs
        return SimpleNamespace(
            returncode=0,
            stdout=json.dumps(
                _receipt(
                    verification_outcome_code="gap_detected",
                    next_action="replan_target_state",
                )
            ),
            stderr="",
        )

    writer = build_target_state_verification_writer(
        "postgresql://ea_runtime@127.0.0.1:5432/ea_core",
        runner=runner,
        base_environment={},
    )
    result = writer(_context(), request)
    assert result["next_action"] == "replan_target_state"


def test_verification_writer_fails_closed_on_runtime_or_receipt_drift() -> None:
    """Database faults and semantically different receipts never look successful."""

    writer = build_target_state_verification_writer(None)
    with pytest.raises(PlannerExecutionError, match="unavailable"):
        writer(
            _context(),
            parse_target_state_verification_request(_PATH, _payload()),
        )

    def timeout_runner(command, **kwargs):
        del command, kwargs
        raise subprocess.TimeoutExpired("psql", 10)

    writer = build_target_state_verification_writer(
        "postgresql://ea_runtime@db.example/ea_core",
        runner=timeout_runner,
    )
    with pytest.raises(PlannerExecutionError, match="database command failed"):
        writer(
            _context(),
            parse_target_state_verification_request(_PATH, _payload()),
        )

    def drift_runner(command, **kwargs):
        del command, kwargs
        return SimpleNamespace(
            returncode=0,
            stdout=json.dumps(_receipt(next_action="done")),
            stderr="",
        )

    writer = build_target_state_verification_writer(
        "postgresql://ea_runtime@db.example/ea_core",
        runner=drift_runner,
    )
    with pytest.raises(PlannerExecutionError, match="invalid verification receipt"):
        writer(
            _context(),
            parse_target_state_verification_request(_PATH, _payload()),
        )
