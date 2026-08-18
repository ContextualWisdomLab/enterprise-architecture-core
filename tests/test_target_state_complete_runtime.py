"""Authenticated runtime acceptance for completing started transformations."""

from __future__ import annotations

import base64
import json
import threading
from http.client import HTTPConnection
from types import SimpleNamespace
from typing import Any

import pytest

import ea_core_foundation.completion_runtime as completion_runtime
from ea_core_foundation.authorization import KeyverseAuthorizationConfig
from ea_core_foundation.completion_runtime import create_runtime_server
from ea_core_foundation.service import BindAddress, PlannerExecutionError

_TENANT_ID = "018f47b2-905a-7b16-bfd4-7e4f53f10e91"
_TRANSFORMATION_ID = "0196e010-1111-7111-8111-111111111191"
_DECISION_REQUEST_ID = "0196e090-1111-7111-8111-111111111193"
_EVIDENCE_ID = "0195d145-64e8-7f4f-8a23-a0cc784cbf10"
_HISTORY_ID = "0196e091-1111-7111-8111-111111111193"
_OUTBOX_ID = "0196e092-1111-7111-8111-111111111193"
_COMPLETE_PATH = f"/v1/architecture-transformations/{_TRANSFORMATION_ID}/complete"
_START_PATH = f"/v1/architecture-transformations/{_TRANSFORMATION_ID}/start"


def _config(
    roles: frozenset[str] = frozenset({"ea_transformation_completer"}),
) -> KeyverseAuthorizationConfig:
    """Return the dedicated Keyverse relying-party profile for completion."""

    return KeyverseAuthorizationConfig(
        issuer_uri="https://id.example/realms/cwl",
        audience="enterprise-architecture-core",
        jwks_url="https://id.example/realms/cwl/protocol/openid-connect/certs",
        tenant_claim="tenant",
        role_claim="role",
        allowed_roles=roles,
    )


def _payload(**changes: object) -> dict[str, object]:
    """Return one valid transformation-completion body with optional mutations."""

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


def _receipt(**changes: object) -> dict[str, object]:
    """Return one valid immutable completion receipt with optional mutations."""

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


def _b64url(value: bytes) -> str:
    """Encode deterministic JWT fixture bytes without padding."""

    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _token(role: str = "ea_transformation_completer") -> str:
    """Build a structurally valid JWT for signature-mocked HTTP acceptance."""

    header = {"alg": "RS256", "kid": "fixture-key", "typ": "JWT"}
    payload = {
        "iss": _config().issuer_uri,
        "aud": _config().audience,
        "exp": 2_000_000_000,
        "sub": "transformation-verifier-123",
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
    payload: object,
    *,
    authorization: str | None,
    path: str = _COMPLETE_PATH,
) -> tuple[int, dict[str, Any]]:
    """Issue one JSON POST and return its response status and object."""

    connection = HTTPConnection(host, port, timeout=2)
    body = json.dumps(payload).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "Content-Length": str(len(body)),
    }
    if authorization is not None:
        headers["Authorization"] = authorization
    try:
        connection.request("POST", path, body=body, headers=headers)
        response = connection.getresponse()
        return response.status, json.loads(response.read().decode("utf-8"))
    finally:
        connection.close()


def _start_server(**kwargs: Any) -> tuple[Any, threading.Thread, str, int]:
    """Start the completion-aware runtime on an ephemeral loopback port."""

    server = create_runtime_server(BindAddress("127.0.0.1", 0), **kwargs)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address[:2]
    return server, thread, host, port


def _stop_server(server: Any, thread: threading.Thread) -> None:
    """Release one in-process runtime."""

    server.shutdown()
    server.server_close()
    thread.join(timeout=2)


def test_http_completion_is_purpose_authorized_and_actionable() -> None:
    """Only a completer can advance a governed started transformation."""

    writes: list[str] = []

    def writer(context: Any, request: Any) -> dict[str, object]:
        del request
        writes.append(context.subject_id)
        return _receipt()

    server, thread, host, port = _start_server(
        complete_authorization_config=_config(),
        jwks_loader=_jwks_loader,
        signature_verifier=lambda signing_input, signature, jwk: True,
        target_state_complete_writer=writer,
    )
    try:
        anonymous_status, anonymous = _post(
            host,
            port,
            _payload(),
            authorization=None,
        )
        denied_status, denied = _post(
            host,
            port,
            _payload(),
            authorization=f"Bearer {_token('ea_reader')}",
        )
        ok_status, ok = _post(
            host,
            port,
            _payload(),
            authorization=f"Bearer {_token()}",
        )
    finally:
        _stop_server(server, thread)

    assert anonymous_status == 401
    assert anonymous["error_code"] == "authorization_required"
    assert denied_status == 403
    assert denied["error_code"] == "forbidden"
    assert ok_status == 201
    assert ok["transformation_state_code"] == "completed"
    assert ok["next_action"] == "verify_target_state"
    assert writes == ["transformation-verifier-123"]


def test_http_completion_replay_returns_200() -> None:
    """Exact replay is observable without presenting a second state transition."""

    server, thread, host, port = _start_server(
        complete_authorization_config=_config(),
        jwks_loader=_jwks_loader,
        signature_verifier=lambda signing_input, signature, jwk: True,
        target_state_complete_writer=lambda context, request: _receipt(replayed=True),
    )
    try:
        status, body = _post(
            host,
            port,
            _payload(),
            authorization=f"Bearer {_token()}",
        )
    finally:
        _stop_server(server, thread)

    assert status == 200
    assert body["replayed"] is True


@pytest.mark.parametrize(
    "kwargs",
    [
        {},
        {
            "complete_authorization_config": "not-a-config",
            "target_state_complete_writer": "not-a-writer",
        },
    ],
)
def test_http_completion_fails_closed_without_policy_and_writer(
    kwargs: dict[str, object],
) -> None:
    """Completion requires both purpose authorization and a command port."""

    server, thread, host, port = _start_server(**kwargs)
    try:
        status, body = _post(
            host,
            port,
            _payload(),
            authorization=f"Bearer {_token()}",
        )
    finally:
        _stop_server(server, thread)

    assert status == 503
    assert body["error_code"] == "completion_unavailable"


def test_http_completion_rejects_invalid_request_before_write() -> None:
    """Malformed completion meaning remains a 400 before command execution."""

    writes: list[str] = []

    def writer(context: Any, request: Any) -> dict[str, object]:
        del context, request
        writes.append("write")
        return {}

    server, thread, host, port = _start_server(
        complete_authorization_config=_config(),
        jwks_loader=_jwks_loader,
        signature_verifier=lambda signing_input, signature, jwk: True,
        target_state_complete_writer=writer,
    )
    try:
        status, body = _post(
            host,
            port,
            _payload(decision_actor_ref="spoofed"),
            authorization=f"Bearer {_token()}",
        )
    finally:
        _stop_server(server, thread)

    assert status == 400
    assert body["error_code"] == "invalid_completion_request"
    assert writes == []


def test_http_completion_returns_retriable_failure_when_writer_raises() -> None:
    """Database state conflicts remain non-success with an actionable retry path."""

    def failing_writer(context: Any, request: Any) -> dict[str, object]:
        del context, request
        raise PlannerExecutionError("conflict")

    server, thread, host, port = _start_server(
        complete_authorization_config=_config(),
        jwks_loader=_jwks_loader,
        signature_verifier=lambda signing_input, signature, jwk: True,
        target_state_complete_writer=failing_writer,
    )
    try:
        status, body = _post(
            host,
            port,
            _payload(),
            authorization=f"Bearer {_token()}",
        )
    finally:
        _stop_server(server, thread)

    assert status == 503
    assert body["error_code"] == "completion_command_failed"
    assert "Refresh" in body["next_action"]


def test_non_completion_post_preserves_start_routing() -> None:
    """The completion extension cannot steal the existing start endpoint."""

    server, thread, host, port = _start_server()
    try:
        status, body = _post(
            host,
            port,
            {},
            authorization=None,
            path=_START_PATH,
        )
    finally:
        _stop_server(server, thread)

    assert status == 503
    assert body["error_code"] == "start_unavailable"


def _patch_main_builders(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    """Replace external startup dependencies while retaining runtime wiring."""

    server = SimpleNamespace(server_close=lambda: None)
    monkeypatch.setattr(
        completion_runtime,
        "resolve_bind_address",
        lambda environ: BindAddress("127.0.0.1", 8080),
    )
    monkeypatch.setattr(completion_runtime, "probe_context_contract", lambda: True)
    monkeypatch.setattr(
        completion_runtime,
        "build_database_readiness_probe",
        lambda dsn: "database_probe",
    )
    for name in (
        "build_keyverse_authorization_config",
        "build_approval_authorization_config",
        "build_schedule_authorization_config",
        "build_start_authorization_config",
        "build_complete_authorization_config",
        "build_target_state_plan_reader",
        "build_target_state_approval_writer",
        "build_target_state_schedule_writer",
        "build_target_state_start_writer",
        "build_target_state_complete_writer",
    ):
        monkeypatch.setattr(completion_runtime, name, lambda value, name=name: name)
    monkeypatch.setattr(
        completion_runtime,
        "create_runtime_server",
        lambda bind_address, **kwargs: server,
    )
    return server


def test_main_closes_runtime_after_normal_service_exit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Normal service exit still closes the listening runtime."""

    server = _patch_main_builders(monkeypatch)
    closed: list[bool] = []
    server.server_close = lambda: closed.append(True)
    monkeypatch.setattr(completion_runtime, "serve_forever", lambda current: None)

    assert completion_runtime.main([]) == 0
    assert closed == [True]


def test_main_closes_runtime_after_keyboard_interrupt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Operator shutdown maps to success while releasing the server."""

    server = _patch_main_builders(monkeypatch)
    closed: list[bool] = []
    server.server_close = lambda: closed.append(True)

    def interrupt(current: object) -> None:
        del current
        raise KeyboardInterrupt

    monkeypatch.setattr(completion_runtime, "serve_forever", interrupt)

    assert completion_runtime.main([]) == 0
    assert closed == [True]
