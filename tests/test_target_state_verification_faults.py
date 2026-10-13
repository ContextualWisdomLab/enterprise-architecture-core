"""Fault-path acceptance for governed target-state verification commands."""

from __future__ import annotations

import json
import subprocess
from typing import Any
from uuid import UUID

import pytest

from ea_core_foundation.authorization import AuthorizationContext
from ea_core_foundation.service import PlannerExecutionError, PlannerRequestError
from ea_core_foundation.verify import (
    TargetStateVerificationRequest,
    build_target_state_verification_writer,
    parse_target_state_verification_request,
)

_TENANT_ID = "018f47b2-905a-7b16-bfd4-7e4f53f10e91"
_TRANSFORMATION_ID = "0196e010-1111-7111-8111-111111111191"
_DECISION_REQUEST_ID = "0196e0a0-1111-7111-8111-111111111193"
_EVIDENCE_ID = "0195d145-64e8-7f4f-8a23-a0cc784cbf10"
_HISTORY_ID = "0196e0a1-1111-7111-8111-111111111193"
_OUTBOX_ID = "0196e0a2-1111-7111-8111-111111111193"
_VERIFY_PATH = f"/v1/architecture-transformations/{_TRANSFORMATION_ID}/verification"


def _context(subject: str = "target-state-verifier-123") -> AuthorizationContext:
    """Return one already-verified verification identity."""

    return AuthorizationContext(
        tenant_record_id=UUID(_TENANT_ID),
        role_code="ea_target_state_verifier",
        subject_id=subject,
        issuer_uri="https://id.example/realms/cwl",
    )


def _payload(**changes: object) -> dict[str, object]:
    """Return one valid verification JSON body with optional mutations."""

    payload: dict[str, object] = {
        "decision_request_id": _DECISION_REQUEST_ID,
        "effective_at": "2027-02-02T00:00:00Z",
        "decision_reason_text": "Evidence confirms the approved target state.",
        "evidence_record_id": _EVIDENCE_ID,
        "verification_outcome_code": "verified",
    }
    payload.update(changes)
    return payload


def _request() -> TargetStateVerificationRequest:
    """Return one valid immutable verification request."""

    return TargetStateVerificationRequest.from_values(
        _TRANSFORMATION_ID,
        _DECISION_REQUEST_ID,
        "2027-02-02T00:00:00Z",
        "Evidence confirms the approved target state.",
        _EVIDENCE_ID,
        "verified",
    )


def _receipt(**changes: object) -> dict[str, object]:
    """Return one database-shaped verification receipt with optional drift."""

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


def _runner_for(receipt: object) -> Any:
    """Return a subprocess runner emitting one JSON value."""

    def runner(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        del kwargs
        return subprocess.CompletedProcess(
            command,
            0,
            stdout=json.dumps(receipt),
            stderr="",
        )

    return runner


@pytest.mark.parametrize(
    ("path", "payload"),
    [
        (f"/wrong/{_TRANSFORMATION_ID}/verification", _payload()),
        (
            "/v1/architecture-transformations/"
            f"{_TRANSFORMATION_ID}/nested/verification",
            _payload(),
        ),
        ("/v1/architecture-transformations//verification", _payload()),
        (f"{_VERIFY_PATH}#fragment", _payload()),
        (_VERIFY_PATH, _payload(evidence_record_id="not-a-uuid")),
        (_VERIFY_PATH, _payload(decision_reason_text="x" * 4097)),
        (_VERIFY_PATH, _payload(decision_reason_text=" ")),
        (_VERIFY_PATH, _payload(effective_at=123)),
        (_VERIFY_PATH, _payload(decision_request_id=123)),
    ],
)
def test_verification_parser_rejects_ambiguous_or_noncanonical_inputs(
    path: str,
    payload: dict[str, object],
) -> None:
    """Unbound paths, identifiers, reasons, and types all fail closed."""

    with pytest.raises(PlannerRequestError):
        parse_target_state_verification_request(path, payload)


def test_verification_request_rejects_non_string_transformation_id() -> None:
    """Direct callers cannot bypass canonical UUID parsing with Python values."""

    with pytest.raises(PlannerRequestError):
        TargetStateVerificationRequest.from_values(  # type: ignore[arg-type]
            None,
            _DECISION_REQUEST_ID,
            "2027-02-02T00:00:00Z",
            "verified evidence",
            _EVIDENCE_ID,
            "verified",
        )


@pytest.mark.parametrize("dsn", ["https://not-postgres.example/ea_core", ""])
def test_verification_writer_fails_closed_without_safe_database_authority(
    dsn: str,
) -> None:
    """No safe PostgreSQL DSN means there is no verification authority."""

    writer = build_target_state_verification_writer(dsn, base_environment={})
    with pytest.raises(PlannerExecutionError, match="unavailable"):
        writer(_context(), _request())


def test_verification_writer_rejects_unbounded_verified_actor_reference() -> None:
    """Verified actor data is bounded before immutable audit history."""

    writer = build_target_state_verification_writer(
        "postgresql://ea_runtime@db.example/ea_core",
        runner=lambda command, **kwargs: pytest.fail("runner should not execute"),
        base_environment={},
    )
    with pytest.raises(PlannerExecutionError, match="actor reference"):
        writer(_context("x" * 3000), _request())


@pytest.mark.parametrize(
    ("runner", "message"),
    [
        (
            lambda command, **kwargs: (_ for _ in ()).throw(OSError("psql missing")),
            "database command failed",
        ),
        (
            lambda command, **kwargs: subprocess.CompletedProcess(
                command, 1, stdout="", stderr="denied"
            ),
            "database query failed",
        ),
        (
            lambda command, **kwargs: subprocess.CompletedProcess(
                command, 0, stdout="not-json", stderr=""
            ),
            "invalid JSON",
        ),
        (_runner_for([]), "invalid verification receipt"),
    ],
)
def test_verification_writer_fails_closed_on_runtime_faults(
    runner: Any,
    message: str,
) -> None:
    """Command and decoding faults never masquerade as verification success."""

    writer = build_target_state_verification_writer(
        "postgresql://ea_runtime@db.example/ea_core",
        runner=runner,
        base_environment={},
    )
    with pytest.raises(PlannerExecutionError, match=message):
        writer(_context(), _request())


@pytest.mark.parametrize(
    "changes",
    [
        {"transformation_history_record_id": "not-a-uuid"},
        {"outbox_event_id": "not-a-uuid"},
        {"verification_recorded_at": "not-a-time"},
        {"architecture_transformation_id": "0196e010-1111-7111-8111-111111111192"},
        {"verification_outcome_code": "gap_detected"},
        {"decision_request_id": "0196e0a0-1111-7111-8111-111111111194"},
        {"replayed": "false"},
        {"next_action": "silently_mutate"},
    ],
)
def test_verification_writer_rejects_receipt_drift(
    changes: dict[str, object],
) -> None:
    """Syntactically valid but different verification meaning fails closed."""

    writer = build_target_state_verification_writer(
        "postgresql://ea_runtime@db.example/ea_core",
        runner=_runner_for(_receipt(**changes)),
        base_environment={},
    )
    with pytest.raises(PlannerExecutionError, match="invalid verification receipt"):
        writer(_context(), _request())
