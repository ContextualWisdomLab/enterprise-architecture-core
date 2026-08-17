"""Buyer acceptance for binding an approved transformation to its remediation milestone."""

from __future__ import annotations

import json
import subprocess
from typing import Any
from uuid import UUID

import pytest

from ea_core_foundation.authorization import AuthorizationContext, KeyverseAuthorizationConfig
from ea_core_foundation.runtime import (
    TargetStateScheduleRequest,
    build_schedule_authorization_config,
    build_target_state_schedule_writer,
    parse_target_state_schedule_request,
)
from ea_core_foundation.service import PlannerExecutionError, PlannerRequestError

_TENANT_ID = "018f47b2-905a-7b16-bfd4-7e4f53f10e91"
_TRANSFORMATION_ID = "0196e010-1111-7111-8111-111111111191"
_MILESTONE_ID = "0196e060-1111-7111-8111-111111111191"
_DECISION_REQUEST_ID = "0196e070-1111-7111-8111-111111111191"
_EVIDENCE_ID = "0195d145-64e8-7f4f-8a23-a0cc784cbf10"


def _config(
    roles: frozenset[str] = frozenset({"ea_transformation_scheduler"}),
) -> KeyverseAuthorizationConfig:
    """Return a closed Keyverse relying-party profile for schedule tests."""

    return KeyverseAuthorizationConfig(
        issuer_uri="https://id.example/realms/cwl",
        audience="enterprise-architecture-core",
        jwks_url="https://id.example/realms/cwl/protocol/openid-connect/certs",
        tenant_claim="tenant",
        role_claim="role",
        allowed_roles=roles,
    )


def _context(subject: str = "transformation-planner-123") -> AuthorizationContext:
    """Return one already-verified scheduler identity."""

    return AuthorizationContext(
        tenant_record_id=UUID(_TENANT_ID),
        role_code="ea_transformation_scheduler",
        subject_id=subject,
        issuer_uri="https://id.example/realms/cwl",
    )


def _payload(**changes: object) -> dict[str, object]:
    """Return one valid schedule command with optional mutations."""

    payload: dict[str, object] = {
        "decision_request_id": _DECISION_REQUEST_ID,
        "initiative_milestone_id": _MILESTONE_ID,
        "effective_at": "2027-01-16T00:00:00Z",
        "decision_reason_text": "Bind the approved target state to the migration milestone.",
        "evidence_record_id": _EVIDENCE_ID,
    }
    payload.update(changes)
    return payload


def _request() -> TargetStateScheduleRequest:
    """Return one exact immutable schedule request."""

    return TargetStateScheduleRequest.from_values(
        _TRANSFORMATION_ID,
        _DECISION_REQUEST_ID,
        _MILESTONE_ID,
        "2027-01-16T00:00:00Z",
        "Bind the approved target state to the migration milestone.",
        _EVIDENCE_ID,
    )


def test_schedule_roles_are_separate_from_read_and_approval_roles() -> None:
    """Scheduling authority cannot be inherited from read or approval authority."""

    environment = {
        "EA_OIDC_ISSUER": _config().issuer_uri,
        "EA_OIDC_AUDIENCE": _config().audience,
        "EA_OIDC_JWKS_URL": _config().jwks_url,
        "EA_TENANT_CLAIM": "tenant",
        "EA_ROLE_CLAIM": "role",
        "EA_READ_ROLES": "ea_reader",
        "EA_APPROVAL_ROLES": "ea_architecture_approver",
        "EA_SCHEDULE_ROLES": "ea_transformation_scheduler",
    }
    assert build_schedule_authorization_config(environment) == _config()
    environment.pop("EA_SCHEDULE_ROLES")
    assert build_schedule_authorization_config(environment) is None


def test_schedule_request_binds_canonical_milestone_and_bitemporal_decision() -> None:
    """A schedule names one canonical milestone and preserves business decision time."""

    request = parse_target_state_schedule_request(
        f"/v1/architecture-transformations/{_TRANSFORMATION_ID}/schedule",
        _payload(),
    )
    assert request.architecture_transformation_id == UUID(_TRANSFORMATION_ID)
    assert request.initiative_milestone_id == UUID(_MILESTONE_ID)
    assert request.decision_request_id == UUID(_DECISION_REQUEST_ID)
    assert request.effective_at.isoformat() == "2027-01-16T00:00:00+00:00"


@pytest.mark.parametrize(
    ("path", "payload"),
    [
        ("/v1/architecture-transformations/not-a-uuid/schedule", _payload()),
        (
            f"/v1/architecture-transformations/{_TRANSFORMATION_ID}/schedule?force=true",
            _payload(),
        ),
        (
            f"/v1/architecture-transformations/{_TRANSFORMATION_ID}/schedule",
            _payload(initiative_milestone_id="00000000-0000-4000-8000-000000000000"),
        ),
        (
            f"/v1/architecture-transformations/{_TRANSFORMATION_ID}/schedule",
            _payload(decision_request_id=_DECISION_REQUEST_ID.upper()),
        ),
        (
            f"/v1/architecture-transformations/{_TRANSFORMATION_ID}/schedule",
            _payload(effective_at="2027-01-16T00:00:00"),
        ),
        (
            f"/v1/architecture-transformations/{_TRANSFORMATION_ID}/schedule",
            _payload(decision_reason_text=" "),
        ),
        (
            f"/v1/architecture-transformations/{_TRANSFORMATION_ID}/schedule",
            _payload(decision_actor_ref="spoofed"),
        ),
    ],
)
def test_schedule_request_rejects_ambiguous_or_noncanonical_input(
    path: str,
    payload: dict[str, object],
) -> None:
    """Malformed identifiers, time, fields, or actor spoofing fail before PostgreSQL."""

    with pytest.raises(PlannerRequestError):
        parse_target_state_schedule_request(path, payload)


def test_schedule_writer_uses_verified_actor_and_returns_actionable_receipt() -> None:
    """The command port derives actor authority and returns the milestone target."""

    calls: list[tuple[list[str], dict[str, Any]]] = []

    def runner(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        calls.append((command, kwargs))
        return subprocess.CompletedProcess(
            command,
            0,
            stdout=json.dumps(
                {
                    "transformation_schedule_record_id": "0196e080-1111-7111-8111-111111111191",
                    "architecture_transformation_id": _TRANSFORMATION_ID,
                    "initiative_milestone_id": _MILESTONE_ID,
                    "decision_request_id": _DECISION_REQUEST_ID,
                    "milestone_target_at": "2027-03-31T00:00:00+00:00",
                    "schedule_recorded_at": "2027-01-16T00:00:01+00:00",
                    "replayed": False,
                    "next_action": "start_transformation",
                }
            ),
            stderr="",
        )

    writer = build_target_state_schedule_writer(
        "postgresql://ea_runtime:secret@db.example/ea_core",
        runner=runner,
        base_environment={},
    )
    receipt = writer(_context(), _request())
    assert receipt["next_action"] == "start_transformation"
    assert receipt["initiative_milestone_id"] == _MILESTONE_ID
    command, kwargs = calls[0]
    assert "schedule_transformation" in " ".join(command)
    assert all("secret" not in value for value in command)
    assert "transformation-planner-123" not in " ".join(command)
    assert "migration milestone" not in " ".join(command)
    assert kwargs["env"]["EA_SCHEDULE_ACTOR_REF"].endswith("#transformation-planner-123")
    assert kwargs["env"]["EA_SCHEDULE_REASON_TEXT"].startswith("Bind the approved")


@pytest.mark.parametrize("dsn", [None, "https://not-postgres.example/ea_core"])
def test_schedule_writer_fails_closed_without_safe_database_authority(
    dsn: str | None,
) -> None:
    """No safe PostgreSQL DSN means there is no scheduling write authority."""

    writer = build_target_state_schedule_writer(dsn, base_environment={})
    with pytest.raises(PlannerExecutionError, match="unavailable"):
        writer(_context(), _request())


def test_schedule_writer_rejects_receipt_not_bound_to_requested_meaning() -> None:
    """A database response for another milestone cannot masquerade as this decision."""

    def runner(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            command,
            0,
            stdout=json.dumps(
                {
                    "architecture_transformation_id": _TRANSFORMATION_ID,
                    "initiative_milestone_id": "0196e060-1111-7111-8111-111111111192",
                    "decision_request_id": _DECISION_REQUEST_ID,
                    "replayed": False,
                    "next_action": "start_transformation",
                }
            ),
            stderr="",
        )

    writer = build_target_state_schedule_writer(
        "postgresql://ea_runtime@db.example/ea_core",
        runner=runner,
        base_environment={},
    )
    with pytest.raises(PlannerExecutionError, match="invalid schedule receipt"):
        writer(_context(), _request())
