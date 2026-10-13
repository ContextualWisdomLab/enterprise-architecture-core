"""Fault-path and canonical-input acceptance for target-state start commands."""

from __future__ import annotations

import json
import subprocess
from typing import Any
from uuid import UUID

import pytest

from ea_core_foundation.authorization import AuthorizationContext
from ea_core_foundation.runtime import (
    TargetStateStartRequest,
    build_target_state_start_writer,
    parse_target_state_start_request,
)
from ea_core_foundation.service import PlannerExecutionError, PlannerRequestError

_TENANT_ID = "018f47b2-905a-7b16-bfd4-7e4f53f10e91"
_TRANSFORMATION_ID = "0196e010-1111-7111-8111-111111111191"
_DECISION_REQUEST_ID = "0196e090-1111-7111-8111-111111111191"
_EVIDENCE_ID = "0195d145-64e8-7f4f-8a23-a0cc784cbf10"
_HISTORY_ID = "0196e091-1111-7111-8111-111111111191"
_OUTBOX_ID = "0196e092-1111-7111-8111-111111111191"
_START_PATH = f"/v1/architecture-transformations/{_TRANSFORMATION_ID}/start"


def _context(subject: str = "transformation-operator-123") -> AuthorizationContext:
    """Return one already-verified transformation starter."""

    return AuthorizationContext(
        tenant_record_id=UUID(_TENANT_ID),
        role_code="ea_transformation_starter",
        subject_id=subject,
        issuer_uri="https://id.example/realms/cwl",
    )


def _request() -> TargetStateStartRequest:
    """Return one immutable valid transformation-start request."""

    return TargetStateStartRequest.from_values(
        _TRANSFORMATION_ID,
        _DECISION_REQUEST_ID,
        "2027-01-17T00:00:00Z",
        "Begin the approved target-state execution.",
        _EVIDENCE_ID,
    )


def _payload(**changes: object) -> dict[str, object]:
    """Return one exact start payload with optional mutations."""

    payload: dict[str, object] = {
        "decision_request_id": _DECISION_REQUEST_ID,
        "effective_at": "2027-01-17T00:00:00Z",
        "decision_reason_text": "Begin the approved target-state execution.",
        "evidence_record_id": _EVIDENCE_ID,
    }
    payload.update(changes)
    return payload


def _valid_receipt(**changes: object) -> dict[str, object]:
    """Return one database-shaped start receipt with optional mutations."""

    receipt: dict[str, object] = {
        "transformation_history_record_id": _HISTORY_ID,
        "architecture_transformation_id": _TRANSFORMATION_ID,
        "transformation_state_code": "started",
        "outbox_event_id": _OUTBOX_ID,
        "decision_request_id": _DECISION_REQUEST_ID,
        "start_recorded_at": "2027-01-17T00:00:01+00:00",
        "replayed": False,
        "next_action": "monitor_transformation",
    }
    receipt.update(changes)
    return receipt


def _runner_for(receipt: object) -> Any:
    """Return a subprocess runner that emits one JSON value."""

    def runner(
        command: list[str],
        **kwargs: Any,
    ) -> subprocess.CompletedProcess[str]:
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
        (f"/wrong/{_TRANSFORMATION_ID}/start", _payload()),
        (
            "/v1/architecture-transformations/"
            f"{_TRANSFORMATION_ID}/nested/start",
            _payload(),
        ),
        ("/v1/architecture-transformations//start", _payload()),
        (f"{_START_PATH}#fragment", _payload()),
        (_START_PATH, _payload(evidence_record_id="not-a-uuid")),
        (_START_PATH, _payload(decision_reason_text="x" * 4097)),
        (_START_PATH, _payload(effective_at=123)),
    ],
)
def test_start_parser_rejects_remaining_ambiguous_inputs(
    path: str,
    payload: dict[str, object],
) -> None:
    """Unbound routes, identifiers, reasons, and typed values fail closed."""

    with pytest.raises(PlannerRequestError):
        parse_target_state_start_request(path, payload)


def test_start_request_rejects_non_string_transformation_id() -> None:
    """Direct callers cannot bypass canonical UUIDv7 parsing with Python values."""

    with pytest.raises(PlannerRequestError):
        TargetStateStartRequest.from_values(  # type: ignore[arg-type]
            None,
            _DECISION_REQUEST_ID,
            "2027-01-17T00:00:00Z",
            "approved",
            _EVIDENCE_ID,
        )


def test_start_writer_rejects_unbounded_verified_actor_reference() -> None:
    """Verified identity data is bounded before reaching the audit function."""

    writer = build_target_state_start_writer(
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
        (_runner_for([]), "invalid start receipt"),
    ],
)
def test_start_writer_fails_closed_on_runtime_faults(
    runner: Any,
    message: str,
) -> None:
    """Command and decoding faults never masquerade as start success."""

    writer = build_target_state_start_writer(
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
        {"start_recorded_at": "not-a-time"},
        {
            "architecture_transformation_id": (
                "0196e010-1111-7111-8111-111111111192"
            )
        },
        {"transformation_state_code": "approved"},
        {"decision_request_id": "0196e090-1111-7111-8111-111111111192"},
        {"replayed": "false"},
        {"next_action": "silently_mutate"},
    ],
)
def test_start_writer_rejects_receipt_drift(
    changes: dict[str, object],
) -> None:
    """Syntactically valid but different receipt meaning fails closed."""

    writer = build_target_state_start_writer(
        "postgresql://ea_runtime@db.example/ea_core",
        runner=_runner_for(_valid_receipt(**changes)),
        base_environment={},
    )
    with pytest.raises(PlannerExecutionError, match="invalid start receipt"):
        writer(_context(), _request())
