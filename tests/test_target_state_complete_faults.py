"""Fault-path acceptance for governed target-state completion commands."""

from __future__ import annotations

import json
import subprocess
from typing import Any
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

_TENANT_ID = "018f47b2-905a-7b16-bfd4-7e4f53f10e91"
_TRANSFORMATION_ID = "0196e010-1111-7111-8111-111111111191"
_DECISION_REQUEST_ID = "0196e090-1111-7111-8111-111111111193"
_EVIDENCE_ID = "0195d145-64e8-7f4f-8a23-a0cc784cbf10"
_HISTORY_ID = "0196e091-1111-7111-8111-111111111193"
_OUTBOX_ID = "0196e092-1111-7111-8111-111111111193"
_COMPLETE_PATH = f"/v1/architecture-transformations/{_TRANSFORMATION_ID}/complete"


def _context(subject: str = "transformation-verifier-123") -> AuthorizationContext:
    """Return one already-verified completion identity."""

    return AuthorizationContext(
        tenant_record_id=UUID(_TENANT_ID),
        role_code="ea_transformation_completer",
        subject_id=subject,
        issuer_uri="https://id.example/realms/cwl",
    )


def _request() -> TargetStateCompleteRequest:
    """Return one valid immutable completion request."""

    return TargetStateCompleteRequest.from_values(
        _TRANSFORMATION_ID,
        _DECISION_REQUEST_ID,
        "2027-02-01T00:00:00Z",
        "Confirm the governed target-state execution is complete.",
        _EVIDENCE_ID,
    )


def _payload(**changes: object) -> dict[str, object]:
    """Return one valid completion JSON body with optional mutations."""

    payload: dict[str, object] = {
        "decision_request_id": _DECISION_REQUEST_ID,
        "effective_at": "2027-02-01T00:00:00Z",
        "decision_reason_text": "Confirm the governed target-state execution is complete.",
        "evidence_record_id": _EVIDENCE_ID,
    }
    payload.update(changes)
    return payload


def _receipt(**changes: object) -> dict[str, object]:
    """Return one database-shaped completion receipt with optional drift."""

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


def _runner_for(receipt: object) -> Any:
    """Return a subprocess runner emitting one JSON value."""

    def runner(
        command: list[str],
        **kwargs: Any,
    ) -> subprocess.CompletedProcess[str]:
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
        (f"/wrong/{_TRANSFORMATION_ID}/complete", _payload()),
        (
            "/v1/architecture-transformations/"
            f"{_TRANSFORMATION_ID}/nested/complete",
            _payload(),
        ),
        ("/v1/architecture-transformations//complete", _payload()),
        (f"{_COMPLETE_PATH}#fragment", _payload()),
        (_COMPLETE_PATH, _payload(evidence_record_id="not-a-uuid")),
        (_COMPLETE_PATH, _payload(decision_reason_text="x" * 4097)),
        (_COMPLETE_PATH, _payload(decision_reason_text=" ")),
        (_COMPLETE_PATH, _payload(effective_at=123)),
        (_COMPLETE_PATH, _payload(decision_actor_ref="spoofed")),
    ],
)
def test_completion_parser_rejects_ambiguous_or_noncanonical_inputs(
    path: str,
    payload: dict[str, object],
) -> None:
    """Unbound routes, identifiers, reasons, types, and actor spoofing fail closed."""

    with pytest.raises(PlannerRequestError):
        parse_target_state_complete_request(path, payload)


def test_completion_request_rejects_non_string_transformation_id() -> None:
    """Direct callers cannot bypass canonical UUID parsing with Python values."""

    with pytest.raises(PlannerRequestError):
        TargetStateCompleteRequest.from_values(  # type: ignore[arg-type]
            None,
            _DECISION_REQUEST_ID,
            "2027-02-01T00:00:00Z",
            "complete",
            _EVIDENCE_ID,
        )


def test_completion_roles_fail_closed_when_not_configured() -> None:
    """Read/start roles cannot silently inherit transformation completion authority."""

    environment = {
        "EA_OIDC_ISSUER": "https://id.example/realms/cwl",
        "EA_OIDC_AUDIENCE": "enterprise-architecture-core",
        "EA_OIDC_JWKS_URL": (
            "https://id.example/realms/cwl/protocol/openid-connect/certs"
        ),
        "EA_TENANT_CLAIM": "tenant",
        "EA_ROLE_CLAIM": "role",
        "EA_READ_ROLES": "ea_reader",
        "EA_START_ROLES": "ea_transformation_starter",
    }
    assert build_complete_authorization_config(environment) is None


@pytest.mark.parametrize("dsn", [None, "https://not-postgres.example/ea_core"])
def test_completion_writer_fails_closed_without_safe_database_authority(
    dsn: str | None,
) -> None:
    """No safe PostgreSQL DSN means there is no completion authority."""

    writer = build_target_state_complete_writer(dsn, base_environment={})
    with pytest.raises(PlannerExecutionError, match="unavailable"):
        writer(_context(), _request())


def test_completion_writer_rejects_unbounded_verified_actor_reference() -> None:
    """Verified actor data is bounded before it can reach immutable audit history."""

    writer = build_target_state_complete_writer(
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
            lambda command, **kwargs: (_ for _ in ()).throw(
                OSError("psql missing")
            ),
            "database command failed",
        ),
        (
            lambda command, **kwargs: (_ for _ in ()).throw(
                subprocess.TimeoutExpired(command, timeout=10)
            ),
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
        (_runner_for([]), "invalid completion receipt"),
    ],
)
def test_completion_writer_fails_closed_on_runtime_faults(
    runner: Any,
    message: str,
) -> None:
    """Command and decoding faults never masquerade as completion success."""

    writer = build_target_state_complete_writer(
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
        {"completion_recorded_at": "not-a-time"},
        {
            "architecture_transformation_id": (
                "0196e010-1111-7111-8111-111111111192"
            )
        },
        {"transformation_state_code": "started"},
        {"decision_request_id": "0196e090-1111-7111-8111-111111111194"},
        {"replayed": "false"},
        {"next_action": "silently_mutate"},
    ],
)
def test_completion_writer_rejects_receipt_drift(
    changes: dict[str, object],
) -> None:
    """Syntactically valid but different completion meaning fails closed."""

    writer = build_target_state_complete_writer(
        "postgresql://ea_runtime@db.example/ea_core",
        runner=_runner_for(_receipt(**changes)),
        base_environment={},
    )
    with pytest.raises(PlannerExecutionError, match="invalid completion receipt"):
        writer(_context(), _request())
