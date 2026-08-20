"""Test-first contract for requesting reassessment after evidence closure."""

from __future__ import annotations

import json
from types import SimpleNamespace
from uuid import UUID

import pytest

from ea_core_foundation.authorization import AuthorizationContext
from ea_core_foundation.data_management_recheck import (
    DataManagementRecheckRequest,
    build_data_management_recheck_authorization_config,
    build_data_management_recheck_writer,
    parse_data_management_recheck_request,
)
from ea_core_foundation.service import PlannerExecutionError, PlannerRequestError

_ASSESSMENT_ID = "0196f300-1111-7111-8111-111111111171"
_ACCEPTANCE_ID = "0196f300-1111-7111-8111-111111111172"
_DECISION_REQUEST_ID = "0196f300-1111-7111-8111-111111111173"
_RECHECK_ID = "0196f300-1111-7111-8111-111111111174"
_OUTBOX_ID = "0196f300-1111-7111-8111-111111111175"
_PATH = f"/v1/data-management-assessments/{_ASSESSMENT_ID}/recheck"


def _payload(**changes: object) -> dict[str, object]:
    """Return one valid reassessment request with optional mutations."""

    payload: dict[str, object] = {
        "trigger_evidence_acceptance_id": _ACCEPTANCE_ID,
        "decision_request_id": _DECISION_REQUEST_ID,
        "requested_at": "2026-08-19T05:00:00Z",
    }
    payload.update(changes)
    return payload


def _context() -> AuthorizationContext:
    """Return one already-verified Keyverse reassessment identity."""

    return AuthorizationContext(
        tenant_record_id=UUID("018f47b2-905a-7b16-bfd4-7e4f53f10e91"),
        role_code="ea_data_management_rechecker",
        subject_id="data-governance-lead-123",
        issuer_uri="https://id.example/realms/cwl",
    )


def _receipt(**changes: object) -> dict[str, object]:
    """Return one database-shaped reassessment receipt."""

    receipt: dict[str, object] = {
        "assessment_recheck_request_id": _RECHECK_ID,
        "outbox_event_id": _OUTBOX_ID,
        "replayed": False,
        "next_action": "await_assessment_recheck",
    }
    receipt.update(changes)
    return receipt


def _stdout_runner(stdout: str):
    """Return a deterministic successful command runner with the supplied output."""

    def runner(command, **kwargs):
        del command, kwargs
        return SimpleNamespace(returncode=0, stdout=stdout, stderr="")

    return runner


def test_parse_recheck_binds_assessment_and_only_documented_fields() -> None:
    """The route owns assessment identity while the body owns decision evidence."""

    request = parse_data_management_recheck_request(_PATH, _payload())
    assert isinstance(request, DataManagementRecheckRequest)
    assert str(request.data_management_assessment_projection_id) == _ASSESSMENT_ID
    assert str(request.trigger_evidence_acceptance_id) == _ACCEPTANCE_ID
    assert str(request.decision_request_id) == _DECISION_REQUEST_ID
    assert request.requested_at.isoformat() == "2026-08-19T05:00:00+00:00"

    with pytest.raises(PlannerRequestError, match="only the documented fields"):
        parse_data_management_recheck_request(
            _PATH,
            _payload(truth_status_code="authoritative"),
        )
    with pytest.raises(PlannerRequestError, match="JSON strings"):
        parse_data_management_recheck_request(_PATH, _payload(requested_at=123))
    with pytest.raises(PlannerRequestError, match="recheck path"):
        parse_data_management_recheck_request(_PATH + "?unsafe=1", _payload())
    with pytest.raises(PlannerRequestError, match="recheck path"):
        parse_data_management_recheck_request(
            "https://attacker.example" + _PATH,
            _payload(),
        )
    with pytest.raises(PlannerRequestError, match="recheck path"):
        parse_data_management_recheck_request("//attacker.example" + _PATH, _payload())
    with pytest.raises(PlannerRequestError, match="recheck path"):
        parse_data_management_recheck_request("/v1/not-recheck", _payload())
    with pytest.raises(PlannerRequestError, match="one assessment UUID"):
        parse_data_management_recheck_request(
            "/v1/data-management-assessments//recheck",
            _payload(),
        )
    with pytest.raises(PlannerRequestError, match="one assessment UUID"):
        parse_data_management_recheck_request(
            f"/v1/data-management-assessments/{_ASSESSMENT_ID}/nested/recheck",
            _payload(),
        )
    with pytest.raises(PlannerRequestError, match="UUIDv7"):
        parse_data_management_recheck_request(
            "/v1/data-management-assessments/not-a-uuid/recheck",
            _payload(),
        )


def test_recheck_authority_is_separate_and_fail_closed() -> None:
    """Read, verification, and replanning roles never inherit reassessment authority."""

    environment = {
        "EA_OIDC_ISSUER": "https://id.example/realms/cwl",
        "EA_OIDC_AUDIENCE": "enterprise-architecture-core",
        "EA_OIDC_JWKS_URL": (
            "https://id.example/realms/cwl/protocol/openid-connect/certs"
        ),
        "EA_TENANT_CLAIM": "tenant",
        "EA_ROLE_CLAIM": "role",
        "EA_READ_ROLES": "ea_reader",
        "EA_REPLAN_ROLES": "ea_target_state_replanner",
        "EA_DATA_MANAGEMENT_RECHECK_ROLES": "ea_data_management_rechecker",
    }
    config = build_data_management_recheck_authorization_config(environment)
    assert config is not None
    assert config.allowed_roles == frozenset({"ea_data_management_rechecker"})

    environment.pop("EA_DATA_MANAGEMENT_RECHECK_ROLES")
    assert build_data_management_recheck_authorization_config(environment) is None


def test_recheck_writer_uses_bounded_command_and_validates_receipt() -> None:
    """The adapter calls the command port and validates buyer receipt meaning."""

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

    request = parse_data_management_recheck_request(_PATH, _payload())
    writer = build_data_management_recheck_writer(
        "postgresql://ea_runtime:secret@127.0.0.1:5432/ea_core",
        runner=runner,
        base_environment={"PATH": "/usr/bin"},
    )
    result = writer(_context(), request)

    command_text = " ".join(captured["command"])
    assert (
        "request_data_management_assessment_recheck_for_tenant" in command_text
    )
    assert "assessment_recheck_request " not in command_text
    assert "data-governance-lead-123" not in command_text
    assert "secret" not in command_text
    assert captured["timeout"] == 10
    assert result["assessment_recheck_request_id"] == _RECHECK_ID
    assert result["outbox_event_id"] == _OUTBOX_ID
    assert result["replayed"] is False
    assert result["next_action"] == "await_assessment_recheck"


def test_recheck_writer_fails_closed_when_storage_is_unavailable() -> None:
    """Missing or malformed PostgreSQL authority returns one rejecting writer."""

    request = parse_data_management_recheck_request(_PATH, _payload())
    for dsn in (None, "https://db.example/ea_core"):
        with pytest.raises(PlannerExecutionError, match="unavailable"):
            build_data_management_recheck_writer(dsn)(_context(), request)


def test_recheck_writer_fails_closed_on_command_transport_errors() -> None:
    """Process failures and transport failures never look like reassessment success."""

    request = parse_data_management_recheck_request(_PATH, _payload())

    def failed_runner(command, **kwargs):
        del command, kwargs
        return SimpleNamespace(returncode=1, stdout="", stderr="boom")

    with pytest.raises(PlannerExecutionError, match="query failed"):
        build_data_management_recheck_writer(
            "postgresql://ea_runtime@db.example/ea_core",
            runner=failed_runner,
        )(_context(), request)

    def unavailable_runner(command, **kwargs):
        del command, kwargs
        raise OSError("psql unavailable")

    with pytest.raises(PlannerExecutionError, match="command failed"):
        build_data_management_recheck_writer(
            "postgresql://ea_runtime@db.example/ea_core",
            runner=unavailable_runner,
        )(_context(), request)


def test_recheck_writer_rejects_invalid_receipt_shapes_and_semantics() -> None:
    """Malformed JSON, expanded shapes, invalid IDs, and semantic drift fail closed."""

    request = parse_data_management_recheck_request(_PATH, _payload())
    cases = [
        ("not-json", "invalid JSON"),
        (json.dumps([]), "invalid reassessment receipt"),
        (
            json.dumps(_receipt(decision_actor_email="buyer@example.com")),
            "invalid reassessment receipt",
        ),
        (
            json.dumps(_receipt(outbox_event_id="not-a-uuid")),
            "invalid reassessment receipt",
        ),
        (
            json.dumps(_receipt(replayed="false")),
            "invalid reassessment receipt",
        ),
        (
            json.dumps(_receipt(next_action="assessment_complete")),
            "invalid reassessment receipt",
        ),
    ]

    for stdout, message in cases:
        with pytest.raises(PlannerExecutionError, match=message):
            build_data_management_recheck_writer(
                "postgresql://ea_runtime@db.example/ea_core",
                runner=_stdout_runner(stdout),
            )(_context(), request)
