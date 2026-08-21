"""Buyer acceptance for starting a governed scheduled transformation."""

from __future__ import annotations

import json
import subprocess
from typing import Any
from uuid import UUID

import pytest

from ea_core_foundation.authorization import (
    AuthorizationContext,
    KeyverseAuthorizationConfig,
)
from ea_core_foundation.runtime import (
    TargetStateStartRequest,
    build_start_authorization_config,
    build_target_state_start_writer,
    parse_target_state_start_request,
)
from ea_core_foundation.service import PlannerExecutionError, PlannerRequestError

_TENANT_ID = "018f47b2-905a-7b16-bfd4-7e4f53f10e91"
_TRANSFORMATION_ID = "0196e010-1111-7111-8111-111111111191"
_DECISION_REQUEST_ID = "0196e090-1111-7111-8111-111111111191"
_EVIDENCE_ID = "0195d145-64e8-7f4f-8a23-a0cc784cbf10"


def _config(
    roles: frozenset[str] = frozenset({"ea_transformation_starter"}),
) -> KeyverseAuthorizationConfig:
    """Return a closed Keyverse relying-party profile for start-command tests."""

    return KeyverseAuthorizationConfig(
        issuer_uri="https://id.example/realms/cwl",
        audience="enterprise-architecture-core",
        jwks_url="https://id.example/realms/cwl/protocol/openid-connect/certs",
        tenant_claim="tenant",
        role_claim="role",
        allowed_roles=roles,
    )


def _context(subject: str = "transformation-operator-123") -> AuthorizationContext:
    """Return one already-verified start-command identity."""

    return AuthorizationContext(
        tenant_record_id=UUID(_TENANT_ID),
        role_code="ea_transformation_starter",
        subject_id=subject,
        issuer_uri="https://id.example/realms/cwl",
    )


def _payload(**changes: object) -> dict[str, object]:
    """Return one valid start command with optional mutations."""

    payload: dict[str, object] = {
        "decision_request_id": _DECISION_REQUEST_ID,
        "effective_at": "2027-01-17T00:00:00Z",
        "decision_reason_text": "Begin the approved target-state execution.",
        "evidence_record_id": _EVIDENCE_ID,
    }
    payload.update(changes)
    return payload


def _request() -> TargetStateStartRequest:
    """Return one exact immutable start request."""

    return TargetStateStartRequest.from_values(
        _TRANSFORMATION_ID,
        _DECISION_REQUEST_ID,
        "2027-01-17T00:00:00Z",
        "Begin the approved target-state execution.",
        _EVIDENCE_ID,
    )


def test_start_roles_are_separate_from_read_approval_and_schedule_roles() -> None:
    """Starting execution cannot inherit authority from other decision surfaces."""

    environment = {
        "EA_OIDC_ISSUER": _config().issuer_uri,
        "EA_OIDC_AUDIENCE": _config().audience,
        "EA_OIDC_JWKS_URL": _config().jwks_url,
        "EA_TENANT_CLAIM": "tenant",
        "EA_ROLE_CLAIM": "role",
        "EA_READ_ROLES": "ea_reader",
        "EA_APPROVAL_ROLES": "ea_architecture_approver",
        "EA_SCHEDULE_ROLES": "ea_transformation_scheduler",
        "EA_START_ROLES": "ea_transformation_starter",
    }
    assert build_start_authorization_config(environment) == _config()
    environment.pop("EA_START_ROLES")
    assert build_start_authorization_config(environment) is None


def test_start_request_binds_canonical_identity_and_business_time() -> None:
    """A start command binds one canonical transformation and effective instant."""

    request = parse_target_state_start_request(
        f"/v1/architecture-transformations/{_TRANSFORMATION_ID}/start",
        _payload(),
    )
    assert request.architecture_transformation_id == UUID(_TRANSFORMATION_ID)
    assert request.decision_request_id == UUID(_DECISION_REQUEST_ID)
    assert request.effective_at.isoformat() == "2027-01-17T00:00:00+00:00"
    assert request.evidence_record_id == UUID(_EVIDENCE_ID)


@pytest.mark.parametrize(
    ("path", "payload"),
    [
        ("/v1/architecture-transformations/not-a-uuid/start", _payload()),
        (
            f"/v1/architecture-transformations/{_TRANSFORMATION_ID}/start?force=true",
            _payload(),
        ),
        (
            f"/v1/architecture-transformations/{_TRANSFORMATION_ID}/start",
            _payload(decision_request_id=_DECISION_REQUEST_ID.upper()),
        ),
        (
            f"/v1/architecture-transformations/{_TRANSFORMATION_ID}/start",
            _payload(effective_at="2027-01-17T00:00:00"),
        ),
        (
            f"/v1/architecture-transformations/{_TRANSFORMATION_ID}/start",
            _payload(decision_reason_text=" "),
        ),
        (
            f"/v1/architecture-transformations/{_TRANSFORMATION_ID}/start",
            _payload(decision_actor_ref="spoofed"),
        ),
    ],
)
def test_start_request_rejects_ambiguous_or_noncanonical_input(
    path: str,
    payload: dict[str, object],
) -> None:
    """Malformed identifiers, time, fields, or actor spoofing fail before SQL."""

    with pytest.raises(PlannerRequestError):
        parse_target_state_start_request(path, payload)


def test_start_writer_uses_verified_actor_and_returns_actionable_receipt() -> None:
    """The command port derives actor authority and returns a monitor action."""

    calls: list[tuple[list[str], dict[str, Any]]] = []

    def runner(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        calls.append((command, kwargs))
        return subprocess.CompletedProcess(
            command,
            0,
            stdout=json.dumps(
                {
                    "transformation_history_record_id": (
                        "0196e091-1111-7111-8111-111111111191"
                    ),
                    "architecture_transformation_id": _TRANSFORMATION_ID,
                    "transformation_state_code": "started",
                    "outbox_event_id": "0196e092-1111-7111-8111-111111111191",
                    "decision_request_id": _DECISION_REQUEST_ID,
                    "start_recorded_at": "2027-01-17T00:00:01+00:00",
                    "replayed": False,
                    "next_action": "monitor_transformation",
                }
            ),
            stderr="",
        )

    writer = build_target_state_start_writer(
        "postgresql://ea_runtime:secret@db.example/ea_core",
        runner=runner,
        base_environment={},
    )
    receipt = writer(_context(), _request())
    assert receipt["transformation_state_code"] == "started"
    assert receipt["next_action"] == "monitor_transformation"
    command, kwargs = calls[0]
    assert "start_scheduled_transformation" in " ".join(command)
    assert all("secret" not in value for value in command)
    assert "transformation-operator-123" not in " ".join(command)
    assert "approved target-state" not in " ".join(command)
    assert kwargs["env"]["EA_START_ACTOR_REF"].endswith(
        "#transformation-operator-123"
    )
    assert kwargs["env"]["EA_START_REASON_TEXT"].startswith("Begin the approved")


@pytest.mark.parametrize("dsn", [None, "https://not-postgres.example/ea_core"])
def test_start_writer_fails_closed_without_safe_database_authority(
    dsn: str | None,
) -> None:
    """No safe PostgreSQL DSN means there is no transformation-start authority."""

    writer = build_target_state_start_writer(dsn, base_environment={})
    with pytest.raises(PlannerExecutionError, match="unavailable"):
        writer(_context(), _request())


def test_start_writer_rejects_receipt_not_bound_to_requested_meaning() -> None:
    """A database response for another transformation cannot satisfy this command."""

    def runner(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            command,
            0,
            stdout=json.dumps(
                {
                    "transformation_history_record_id": (
                        "0196e091-1111-7111-8111-111111111191"
                    ),
                    "architecture_transformation_id": (
                        "0196e010-1111-7111-8111-111111111192"
                    ),
                    "transformation_state_code": "started",
                    "outbox_event_id": "0196e092-1111-7111-8111-111111111191",
                    "decision_request_id": _DECISION_REQUEST_ID,
                    "start_recorded_at": "2027-01-17T00:00:01+00:00",
                    "replayed": False,
                    "next_action": "monitor_transformation",
                }
            ),
            stderr="",
        )

    writer = build_target_state_start_writer(
        "postgresql://ea_runtime@db.example/ea_core",
        runner=runner,
        base_environment={},
    )
    with pytest.raises(PlannerExecutionError, match="invalid start receipt"):
        writer(_context(), _request())
