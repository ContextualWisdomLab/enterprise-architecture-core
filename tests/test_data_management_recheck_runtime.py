"""HTTP acceptance for the purpose-bound data-management reassessment command."""

from __future__ import annotations

import json
import tomllib
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

import ea_core_foundation.replan_runtime as replan_runtime
from ea_core_foundation.service import PlannerExecutionError
from tests.test_data_management_recheck_api import (
    _ASSESSMENT_ID,
    _payload,
    _receipt,
)
from tests.test_target_state_replan_runtime import (
    _config,
    _get,
    _jwks_loader,
    _patch_main_builders,
    _post,
    _start_server,
    _stop_server,
    _token,
)

_REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
_RECHECK_PATH = f"/v1/data-management-assessments/{_ASSESSMENT_ID}/recheck"
_RECHECK_ROLE = "ea_data_management_rechecker"
_NON_V7_UUID = "550e8400-e29b-41d4-a716-446655440000"


def _recheck_config():
    """Return the dedicated Keyverse policy for reassessment requests."""

    return _config(frozenset({_RECHECK_ROLE}))


def test_http_recheck_is_purpose_authorized_and_actionable() -> None:
    """Only the reassessment role can execute the evidence-closure next action."""

    writes: list[str] = []

    def writer(context: Any, request: Any) -> dict[str, object]:
        writes.append(f"{context.subject_id}:{request.decision_request_id}")
        return _receipt()

    server, thread, host, port = _start_server(
        data_management_recheck_authorization_config=_recheck_config(),
        jwks_loader=_jwks_loader,
        signature_verifier=lambda signing_input, signature, jwk: True,
        data_management_recheck_writer=writer,
    )
    try:
        anonymous_status, anonymous = _post(
            host,
            port,
            authorization=None,
            path=_RECHECK_PATH,
            payload=_payload(),
        )
        denied_status, denied = _post(
            host,
            port,
            authorization=f"Bearer {_token('ea_reader')}",
            path=_RECHECK_PATH,
            payload=_payload(),
        )
        ok_status, ok = _post(
            host,
            port,
            authorization=f"Bearer {_token(_RECHECK_ROLE)}",
            path=_RECHECK_PATH,
            payload=_payload(),
        )
    finally:
        _stop_server(server, thread)

    assert anonymous_status == 401
    assert anonymous["error_code"] == "authorization_required"
    assert denied_status == 403
    assert denied["error_code"] == "forbidden"
    assert ok_status == 200
    assert ok["next_action"] == "await_assessment_recheck"
    assert writes == [
        "target-state-replanner-123:0196f300-1111-7111-8111-111111111173"
    ]


@pytest.mark.parametrize(
    "kwargs",
    [
        {},
        {
            "data_management_recheck_authorization_config": "not-a-config",
            "data_management_recheck_writer": "not-a-writer",
        },
    ],
)
def test_http_recheck_fails_closed_without_policy_and_writer(
    kwargs: dict[str, object],
) -> None:
    """Reject reassessment unless both policy and command port are available."""

    server, thread, host, port = _start_server(**kwargs)
    try:
        status, body = _post(
            host,
            port,
            authorization=f"Bearer {_token(_RECHECK_ROLE)}",
            path=_RECHECK_PATH,
            payload=_payload(),
        )
    finally:
        _stop_server(server, thread)

    assert status == 503
    assert body["error_code"] == "data_management_recheck_unavailable"


def test_http_recheck_rejects_invalid_request_before_write() -> None:
    """Unknown reassessment fields fail before the database writer is invoked."""

    writes: list[str] = []

    def writer(context: Any, request: Any) -> dict[str, object]:
        del context, request
        writes.append("write")
        return _receipt()

    server, thread, host, port = _start_server(
        data_management_recheck_authorization_config=_recheck_config(),
        jwks_loader=_jwks_loader,
        signature_verifier=lambda signing_input, signature, jwk: True,
        data_management_recheck_writer=writer,
    )
    invalid = _payload(truth_status_code="authoritative")
    try:
        status, body = _post(
            host,
            port,
            authorization=f"Bearer {_token(_RECHECK_ROLE)}",
            path=_RECHECK_PATH,
            payload=invalid,
        )
    finally:
        _stop_server(server, thread)

    assert status == 400
    assert body["error_code"] == "invalid_data_management_recheck_request"
    assert writes == []


@pytest.mark.parametrize(
    "request_target",
    [
        f"https://attacker.example{_RECHECK_PATH}",
        f"//attacker.example{_RECHECK_PATH}",
    ],
)
def test_http_recheck_rejects_authority_bearing_request_target(
    request_target: str,
) -> None:
    """Absolute and network-path request targets cannot alias the local command."""

    writes: list[str] = []

    def writer(context: Any, request: Any) -> dict[str, object]:
        del context, request
        writes.append("write")
        return _receipt()

    server, thread, host, port = _start_server(
        data_management_recheck_authorization_config=_recheck_config(),
        jwks_loader=_jwks_loader,
        signature_verifier=lambda signing_input, signature, jwk: True,
        data_management_recheck_writer=writer,
    )
    try:
        status, body = _post(
            host,
            port,
            authorization=f"Bearer {_token(_RECHECK_ROLE)}",
            path=request_target,
            payload=_payload(),
        )
    finally:
        _stop_server(server, thread)

    assert status == 400
    assert body["error_code"] == "invalid_data_management_recheck_request"
    assert writes == []


def test_http_recheck_returns_retriable_failure_when_writer_raises() -> None:
    """Database command failure remains non-success with an explicit retry action."""

    def failing_writer(context: Any, request: Any) -> dict[str, object]:
        del context, request
        raise PlannerExecutionError("database unavailable")

    server, thread, host, port = _start_server(
        data_management_recheck_authorization_config=_recheck_config(),
        jwks_loader=_jwks_loader,
        signature_verifier=lambda signing_input, signature, jwk: True,
        data_management_recheck_writer=failing_writer,
    )
    try:
        status, body = _post(
            host,
            port,
            authorization=f"Bearer {_token(_RECHECK_ROLE)}",
            path=_RECHECK_PATH,
            payload=_payload(),
        )
    finally:
        _stop_server(server, thread)

    assert status == 503
    assert body["error_code"] == "data_management_recheck_command_failed"
    assert "retry" in body["next_action"].lower()


def test_http_recheck_fails_closed_on_unexpected_writer_error() -> None:
    """Unexpected command-port defects return a retriable 503 instead of dropping HTTP."""

    def failing_writer(context: Any, request: Any) -> dict[str, object]:
        del context, request
        raise RuntimeError("unexpected adapter failure")

    server, thread, host, port = _start_server(
        data_management_recheck_authorization_config=_recheck_config(),
        jwks_loader=_jwks_loader,
        signature_verifier=lambda signing_input, signature, jwk: True,
        data_management_recheck_writer=failing_writer,
    )
    try:
        status, body = _post(
            host,
            port,
            authorization=f"Bearer {_token(_RECHECK_ROLE)}",
            path=_RECHECK_PATH,
            payload=_payload(),
        )
    finally:
        _stop_server(server, thread)

    assert status == 503
    assert body["error_code"] == "data_management_recheck_command_failed"
    assert "retry" in body["next_action"].lower()


def test_non_recheck_route_preserves_existing_runtime_routing() -> None:
    """The reassessment route cannot steal inherited readiness behavior."""

    server, thread, host, port = _start_server(
        contract_ready=True,
        database_probe=lambda: True,
    )
    try:
        status, body = _get(host, port, "/ready")
    finally:
        _stop_server(server, thread)

    assert status == 200
    assert body["status_code"] == "ready"


def test_main_wires_recheck_policy_and_writer(monkeypatch: pytest.MonkeyPatch) -> None:
    """Production startup composes reassessment with every existing runtime surface."""

    server = _patch_main_builders(monkeypatch)
    monkeypatch.setattr(
        replan_runtime,
        "build_data_management_recheck_authorization_config",
        lambda value: "build_data_management_recheck_authorization_config",
    )
    monkeypatch.setattr(
        replan_runtime,
        "build_data_management_recheck_writer",
        lambda value: "build_data_management_recheck_writer",
    )
    monkeypatch.setattr(replan_runtime, "serve_forever", lambda current: None)

    assert replan_runtime.main([]) == 0
    assert server.captured["data_management_recheck_authorization_config"] == (
        "build_data_management_recheck_authorization_config"
    )
    assert server.captured["data_management_recheck_writer"] == (
        "build_data_management_recheck_writer"
    )


def test_recheck_route_role_and_openapi_contract_are_published() -> None:
    """Operators and clients can discover the authenticated reassessment action."""

    openapi = json.loads((_REPOSITORY_ROOT / "contracts/openapi.json").read_text())
    environment_example = (_REPOSITORY_ROOT / ".env.example").read_text()
    pyproject = tomllib.loads((_REPOSITORY_ROOT / "pyproject.toml").read_text())

    operation = openapi["paths"][
        "/v1/data-management-assessments/"
        "{data_management_assessment_projection_id}/recheck"
    ]["post"]
    assert operation["operationId"] == "requestDataManagementAssessmentRecheck"
    assert operation["requestBody"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/DataManagementAssessmentRecheckRequest"
    }
    response_schema = operation["responses"]["200"]["content"]["application/json"]
    assert response_schema["schema"] == {
        "$ref": "#/components/schemas/DataManagementAssessmentRecheckReceipt"
    }
    assert "EA_DATA_MANAGEMENT_RECHECK_ROLES=" in environment_example
    assert pyproject["project"]["scripts"]["ea-core"] == (
        "ea_core_foundation.replan_runtime:main"
    )


def test_recheck_openapi_enforces_canonical_uuid7_identifiers() -> None:
    """Published identifier schemas reject UUID versions/runtime spellings we reject."""

    openapi = json.loads((_REPOSITORY_ROOT / "contracts/openapi.json").read_text())
    operation = openapi["paths"][
        "/v1/data-management-assessments/"
        "{data_management_assessment_projection_id}/recheck"
    ]["post"]
    schemas = openapi["components"]["schemas"]
    request_properties = schemas["DataManagementAssessmentRecheckRequest"][
        "properties"
    ]
    receipt_properties = schemas["DataManagementAssessmentRecheckReceipt"]["properties"]
    identifier_schemas = [
        operation["parameters"][0]["schema"],
        request_properties["trigger_evidence_acceptance_id"],
        request_properties["decision_request_id"],
        receipt_properties["assessment_recheck_request_id"],
        receipt_properties["outbox_event_id"],
    ]

    for schema in identifier_schemas:
        validator = Draft202012Validator(schema)
        validator.validate(_ASSESSMENT_ID)
        with pytest.raises(ValidationError):
            validator.validate(_NON_V7_UUID)
        with pytest.raises(ValidationError):
            validator.validate(_ASSESSMENT_ID.upper())
