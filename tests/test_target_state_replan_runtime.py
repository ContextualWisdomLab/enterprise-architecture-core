"""End-to-end runtime and contract acceptance for target-state replanning."""

from __future__ import annotations

import base64
import json
import threading
import tomllib
from http.client import HTTPConnection
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

import ea_core_foundation.replan_runtime as replan_runtime
from ea_core_foundation.authorization import KeyverseAuthorizationConfig
from ea_core_foundation.service import BindAddress, PlannerExecutionError
from tests.test_target_state_replan_api import _PATH, _payload, _receipt

_TENANT_ID = "018f47b2-905a-7b16-bfd4-7e4f53f10e91"
_REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def _config(
    roles: frozenset[str] = frozenset({"ea_target_state_replanner"}),
) -> KeyverseAuthorizationConfig:
    """Return the dedicated Keyverse relying-party profile for replanning."""

    return KeyverseAuthorizationConfig(
        issuer_uri="https://id.example/realms/cwl",
        audience="enterprise-architecture-core",
        jwks_url="https://id.example/realms/cwl/protocol/openid-connect/certs",
        tenant_claim="tenant",
        role_claim="role",
        allowed_roles=roles,
    )


def _b64url(value: bytes) -> str:
    """Encode deterministic JWT fixture bytes without padding."""

    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _token(role: str = "ea_target_state_replanner") -> str:
    """Build a structurally valid JWT for signature-mocked HTTP acceptance."""

    header = {"alg": "RS256", "kid": "fixture-key", "typ": "JWT"}
    payload = {
        "iss": _config().issuer_uri,
        "aud": _config().audience,
        "exp": 2_000_000_000,
        "sub": "target-state-replanner-123",
        "tenant": _TENANT_ID,
        "role": role,
    }
    return ".".join(
        (
            _b64url(json.dumps(header, separators=(",", ":")).encode()),
            _b64url(json.dumps(payload, separators=(",", ":")).encode()),
            _b64url(b"test-signature"),
        )
    )


def _jwks_loader(url: str, issuer: str) -> dict[str, Any]:
    """Return one fixture signing key while asserting the Keyverse boundary."""

    assert url == _config().jwks_url
    assert issuer == _config().issuer_uri
    return {
        "keys": [
            {
                "kty": "RSA",
                "kid": "fixture-key",
                "alg": "RS256",
                "use": "sig",
                "n": "AQAB",
                "e": "AQAB",
            }
        ]
    }


def _post(
    host: str,
    port: int,
    *,
    authorization: str | None,
    path: str = _PATH,
    payload: dict[str, object] | None = None,
) -> tuple[int, dict[str, Any]]:
    """Issue one JSON POST and return the status plus decoded response object."""

    connection = HTTPConnection(host, port, timeout=2)
    headers = {"Content-Type": "application/json"}
    if authorization is not None:
        headers["Authorization"] = authorization
    body = json.dumps(_payload() if payload is None else payload)
    try:
        connection.request("POST", path, body=body, headers=headers)
        response = connection.getresponse()
        raw = response.read()
        return response.status, json.loads(raw.decode("utf-8"))
    finally:
        connection.close()


def _get(host: str, port: int, path: str) -> tuple[int, dict[str, Any]]:
    """Issue one inherited GET request to prove earlier routes remain available."""

    connection = HTTPConnection(host, port, timeout=2)
    try:
        connection.request("GET", path)
        response = connection.getresponse()
        raw = response.read()
        return response.status, json.loads(raw.decode("utf-8"))
    finally:
        connection.close()


def _start_server(**kwargs: Any) -> tuple[Any, threading.Thread, str, int]:
    """Start the replan-aware runtime on an ephemeral loopback port."""

    server = replan_runtime.create_runtime_server(BindAddress("127.0.0.1", 0), **kwargs)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address[:2]
    return server, thread, host, port


def _stop_server(server: Any, thread: threading.Thread) -> None:
    """Release one in-process runtime."""

    server.shutdown()
    server.server_close()
    thread.join(timeout=2)


def test_http_replan_is_purpose_authorized_and_actionable() -> None:
    """Only a replanning identity can create the governed replacement proposal."""

    writes: list[str] = []

    def writer(context: Any, request: Any) -> dict[str, object]:
        writes.append(
            f"{context.subject_id}:{request.replacement_architecture_transformation_id}"
        )
        return _receipt()

    server, thread, host, port = _start_server(
        replan_authorization_config=_config(),
        jwks_loader=_jwks_loader,
        signature_verifier=lambda signing_input, signature, jwk: True,
        target_state_replan_writer=writer,
    )
    try:
        anonymous_status, anonymous = _post(host, port, authorization=None)
        denied_status, denied = _post(
            host,
            port,
            authorization=f"Bearer {_token('ea_target_state_verifier')}",
        )
        ok_status, ok = _post(
            host,
            port,
            authorization=f"Bearer {_token()}",
        )
    finally:
        _stop_server(server, thread)

    assert anonymous_status == 401
    assert anonymous["error_code"] == "authorization_required"
    assert denied_status == 403
    assert denied["error_code"] == "forbidden"
    assert ok_status == 201
    assert ok["next_action"] == "approve_target_state"
    assert writes == [
        "target-state-replanner-123:0196e110-1111-7111-8111-111111111191"
    ]


@pytest.mark.parametrize(
    "kwargs",
    [
        {},
        {
            "replan_authorization_config": "not-a-config",
            "target_state_replan_writer": "not-a-writer",
        },
    ],
)
def test_http_replan_fails_closed_without_policy_and_writer(
    kwargs: dict[str, object],
) -> None:
    """Replanning requires both a purpose policy and its bounded database port."""

    server, thread, host, port = _start_server(**kwargs)
    try:
        status, body = _post(
            host,
            port,
            authorization=f"Bearer {_token()}",
        )
    finally:
        _stop_server(server, thread)

    assert status == 503
    assert body["error_code"] == "replan_unavailable"


def test_http_replan_rejects_invalid_request_before_write() -> None:
    """Malformed replacement meaning stays a 400 before database execution."""

    writes: list[str] = []

    def writer(context: Any, request: Any) -> dict[str, object]:
        del context, request
        writes.append("write")
        return _receipt()

    server, thread, host, port = _start_server(
        replan_authorization_config=_config(),
        jwks_loader=_jwks_loader,
        signature_verifier=lambda signing_input, signature, jwk: True,
        target_state_replan_writer=writer,
    )
    invalid = _payload()
    invalid["replacement_architecture_transformation_id"] = _PATH.split("/")[-2]
    try:
        status, body = _post(
            host,
            port,
            authorization=f"Bearer {_token()}",
            payload=invalid,
        )
    finally:
        _stop_server(server, thread)

    assert status == 400
    assert body["error_code"] == "invalid_replan_request"
    assert writes == []


def test_http_replan_returns_retriable_failure_when_writer_raises() -> None:
    """Database command failures remain non-success with an actionable retry path."""

    def failing_writer(context: Any, request: Any) -> dict[str, object]:
        del context, request
        raise PlannerExecutionError("database unavailable")

    server, thread, host, port = _start_server(
        replan_authorization_config=_config(),
        jwks_loader=_jwks_loader,
        signature_verifier=lambda signing_input, signature, jwk: True,
        target_state_replan_writer=failing_writer,
    )
    try:
        status, body = _post(
            host,
            port,
            authorization=f"Bearer {_token()}",
        )
    finally:
        _stop_server(server, thread)

    assert status == 503
    assert body["error_code"] == "replan_command_failed"
    assert "retry" in body["next_action"].lower()


def test_non_replan_get_preserves_existing_runtime_routing() -> None:
    """The replanning route cannot steal inherited readiness behavior."""

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


def _patch_main_builders(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    """Replace startup dependencies while retaining complete replanning wiring."""

    server = SimpleNamespace(server_close=lambda: None)
    monkeypatch.setattr(
        replan_runtime,
        "resolve_bind_address",
        lambda environ: BindAddress("127.0.0.1", 8080),
    )
    monkeypatch.setattr(replan_runtime, "probe_context_contract", lambda: True)
    monkeypatch.setattr(
        replan_runtime,
        "build_database_readiness_probe",
        lambda dsn: "database_probe",
    )
    for name in (
        "build_keyverse_authorization_config",
        "build_approval_authorization_config",
        "build_schedule_authorization_config",
        "build_start_authorization_config",
        "build_complete_authorization_config",
        "build_verification_authorization_config",
        "build_monitoring_authorization_config",
        "build_replan_authorization_config",
        "build_target_state_plan_reader",
        "build_target_state_approval_writer",
        "build_target_state_schedule_writer",
        "build_target_state_start_writer",
        "build_target_state_complete_writer",
        "build_target_state_verification_writer",
        "build_target_state_monitoring_reader",
        "build_target_state_replan_writer",
    ):
        monkeypatch.setattr(replan_runtime, name, lambda value, name=name: name)
    captured: dict[str, object] = {}

    def create_server(bind_address: BindAddress, **kwargs: object):
        captured["bind_address"] = bind_address
        captured.update(kwargs)
        return server

    monkeypatch.setattr(replan_runtime, "create_runtime_server", create_server)
    server.captured = captured
    return server


def test_main_wires_replan_and_closes_after_exit_or_interrupt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Compose replanning with prior ports and close the runtime safely."""

    server = _patch_main_builders(monkeypatch)
    closed: list[bool] = []
    server.server_close = lambda: closed.append(True)
    monkeypatch.setattr(replan_runtime, "serve_forever", lambda current: None)
    assert replan_runtime.main([]) == 0
    assert closed == [True]
    assert server.captured["replan_authorization_config"] == (
        "build_replan_authorization_config"
    )
    assert server.captured["target_state_replan_writer"] == (
        "build_target_state_replan_writer"
    )

    closed.clear()

    def interrupt(current: object) -> None:
        del current
        raise KeyboardInterrupt

    monkeypatch.setattr(replan_runtime, "serve_forever", interrupt)
    assert replan_runtime.main([]) == 0
    assert closed == [True]


def test_replan_route_event_role_and_entrypoint_are_published() -> None:
    """Expose replanning through every canonical operator surface."""

    openapi = json.loads((_REPOSITORY_ROOT / "contracts/openapi.json").read_text())
    asyncapi = json.loads((_REPOSITORY_ROOT / "contracts/asyncapi.json").read_text())
    pyproject = tomllib.loads((_REPOSITORY_ROOT / "pyproject.toml").read_text())
    environment_example = (_REPOSITORY_ROOT / ".env.example").read_text()

    path = "/v1/architecture-transformations/{architecture_transformation_id}/replan"
    assert openapi["paths"][path]["post"]["operationId"] == (
        "replanTechnologyTargetState"
    )
    assert (
        asyncapi["channels"]["transformationReplanEvents"]["address"]
        == "org.contextualwisdomlab.ea.transformation.replanned.v1"
    )
    assert "publishTransformationReplanned" in asyncapi["operations"]
    assert pyproject["project"]["scripts"]["ea-core"] == (
        "ea_core_foundation.replan_runtime:main"
    )
    assert "EA_REPLAN_ROLES=" in environment_example
