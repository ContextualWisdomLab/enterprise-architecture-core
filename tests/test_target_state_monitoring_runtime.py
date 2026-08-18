"""Authenticated runtime acceptance for target-state monitoring freshness."""

from __future__ import annotations

import base64
import json
import threading
from http.client import HTTPConnection
from types import SimpleNamespace
from typing import Any

import pytest

import ea_core_foundation.monitoring_runtime as monitoring_runtime
from ea_core_foundation.authorization import KeyverseAuthorizationConfig
from ea_core_foundation.service import BindAddress, PlannerExecutionError
from tests.test_target_state_monitoring_api import (
    _EVIDENCE_ID,
    _TRANSFORMATION_ID,
    _status,
)

_TENANT_ID = "018f47b2-905a-7b16-bfd4-7e4f53f10e91"
_PATH = (
    f"/v1/architecture-transformations/{_TRANSFORMATION_ID}/monitoring"
    "?valid_at=2027-03-01T00:00:00Z"
    "&recorded_at=2027-03-01T00:00:00Z"
    "&max_evidence_age_days=90"
)


def _config(
    roles: frozenset[str] = frozenset({"ea_target_state_monitor"}),
) -> KeyverseAuthorizationConfig:
    """Return the dedicated Keyverse relying-party profile for monitoring."""

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


def _token(role: str = "ea_target_state_monitor") -> str:
    """Build a structurally valid JWT for signature-mocked HTTP acceptance."""

    header = {"alg": "RS256", "kid": "fixture-key", "typ": "JWT"}
    payload = {
        "iss": _config().issuer_uri,
        "aud": _config().audience,
        "exp": 2_000_000_000,
        "sub": "target-state-monitor-123",
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


def _get(
    host: str,
    port: int,
    *,
    authorization: str | None,
    path: str = _PATH,
) -> tuple[int, dict[str, Any]]:
    """Issue one GET and return the status and decoded response object."""

    connection = HTTPConnection(host, port, timeout=2)
    headers: dict[str, str] = {}
    if authorization is not None:
        headers["Authorization"] = authorization
    try:
        connection.request("GET", path, headers=headers)
        response = connection.getresponse()
        raw = response.read()
        return response.status, json.loads(raw.decode("utf-8"))
    finally:
        connection.close()


def _start_server(**kwargs: Any) -> tuple[Any, threading.Thread, str, int]:
    """Start the monitoring-aware runtime on an ephemeral loopback port."""

    server = monitoring_runtime.create_runtime_server(
        BindAddress("127.0.0.1", 0), **kwargs
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address[:2]
    return server, thread, host, port


def _stop_server(server: Any, thread: threading.Thread) -> None:
    """Release one in-process runtime."""

    server.shutdown()
    server.server_close()
    thread.join(timeout=2)


def test_http_monitoring_is_purpose_authorized_and_actionable() -> None:
    """Only a monitoring identity can read exact target-state freshness evidence."""

    reads: list[str] = []

    def reader(context: Any, request: Any) -> dict[str, object]:
        reads.append(f"{context.subject_id}:{request.max_evidence_age_days}")
        return _status()

    server, thread, host, port = _start_server(
        monitoring_authorization_config=_config(),
        jwks_loader=_jwks_loader,
        signature_verifier=lambda signing_input, signature, jwk: True,
        target_state_monitoring_reader=reader,
    )
    try:
        anonymous_status, anonymous = _get(host, port, authorization=None)
        denied_status, denied = _get(
            host,
            port,
            authorization=f"Bearer {_token('ea_reader')}",
        )
        ok_status, ok = _get(
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
    assert ok_status == 200
    assert ok["evidence_record_id"] == _EVIDENCE_ID
    assert ok["next_action"] == "continue_monitoring"
    assert reads == ["target-state-monitor-123:90"]


@pytest.mark.parametrize(
    "kwargs",
    [
        {},
        {
            "monitoring_authorization_config": "not-a-config",
            "target_state_monitoring_reader": "not-a-reader",
        },
    ],
)
def test_http_monitoring_fails_closed_without_policy_and_reader(
    kwargs: dict[str, object],
) -> None:
    """Monitoring requires both a purpose policy and its bounded database port."""

    server, thread, host, port = _start_server(**kwargs)
    try:
        status, body = _get(
            host,
            port,
            authorization=f"Bearer {_token()}",
        )
    finally:
        _stop_server(server, thread)

    assert status == 503
    assert body["error_code"] == "monitoring_unavailable"


def test_http_monitoring_rejects_invalid_request_before_read() -> None:
    """Malformed temporal policy stays a 400 before database execution."""

    reads: list[str] = []

    def reader(context: Any, request: Any) -> dict[str, object]:
        del context, request
        reads.append("read")
        return _status()

    server, thread, host, port = _start_server(
        monitoring_authorization_config=_config(),
        jwks_loader=_jwks_loader,
        signature_verifier=lambda signing_input, signature, jwk: True,
        target_state_monitoring_reader=reader,
    )
    try:
        status, body = _get(
            host,
            port,
            authorization=f"Bearer {_token()}",
            path=_PATH.replace("max_evidence_age_days=90", "max_evidence_age_days=0"),
        )
    finally:
        _stop_server(server, thread)

    assert status == 400
    assert body["error_code"] == "invalid_monitoring_request"
    assert reads == []


def test_http_monitoring_returns_retriable_failure_when_reader_raises() -> None:
    """Database read failures remain non-success with an actionable retry path."""

    def failing_reader(context: Any, request: Any) -> dict[str, object]:
        del context, request
        raise PlannerExecutionError("database unavailable")

    server, thread, host, port = _start_server(
        monitoring_authorization_config=_config(),
        jwks_loader=_jwks_loader,
        signature_verifier=lambda signing_input, signature, jwk: True,
        target_state_monitoring_reader=failing_reader,
    )
    try:
        status, body = _get(
            host,
            port,
            authorization=f"Bearer {_token()}",
        )
    finally:
        _stop_server(server, thread)

    assert status == 503
    assert body["error_code"] == "monitoring_query_failed"
    assert "retry" in body["next_action"].lower()


def test_non_monitoring_get_preserves_existing_runtime_routing() -> None:
    """The monitoring route cannot steal the inherited readiness endpoint."""

    server, thread, host, port = _start_server(
        contract_ready=True,
        database_probe=lambda: True,
    )
    try:
        status, body = _get(host, port, authorization=None, path="/readyz")
    finally:
        _stop_server(server, thread)

    assert status == 200
    assert body["status"] == "ready"


def _patch_main_builders(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    """Replace startup dependencies while retaining complete monitoring wiring."""

    server = SimpleNamespace(server_close=lambda: None)
    monkeypatch.setattr(
        monitoring_runtime,
        "resolve_bind_address",
        lambda environ: BindAddress("127.0.0.1", 8080),
    )
    monkeypatch.setattr(monitoring_runtime, "probe_context_contract", lambda: True)
    monkeypatch.setattr(
        monitoring_runtime,
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
        "build_target_state_plan_reader",
        "build_target_state_approval_writer",
        "build_target_state_schedule_writer",
        "build_target_state_start_writer",
        "build_target_state_complete_writer",
        "build_target_state_verification_writer",
        "build_target_state_monitoring_reader",
    ):
        monkeypatch.setattr(monitoring_runtime, name, lambda value, name=name: name)
    captured: dict[str, object] = {}

    def create_server(bind_address: BindAddress, **kwargs: object):
        captured["bind_address"] = bind_address
        captured.update(kwargs)
        return server

    monkeypatch.setattr(monitoring_runtime, "create_runtime_server", create_server)
    server.captured = captured
    return server


def test_main_wires_monitoring_and_closes_after_exit_or_interrupt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Startup composes monitoring with every earlier governed port and closes cleanly."""

    server = _patch_main_builders(monkeypatch)
    closed: list[bool] = []
    server.server_close = lambda: closed.append(True)
    monkeypatch.setattr(monitoring_runtime, "serve_forever", lambda current: None)
    assert monitoring_runtime.main([]) == 0
    assert closed == [True]
    assert server.captured["monitoring_authorization_config"] == (
        "build_monitoring_authorization_config"
    )
    assert server.captured["target_state_monitoring_reader"] == (
        "build_target_state_monitoring_reader"
    )

    closed.clear()

    def interrupt(current: object) -> None:
        del current
        raise KeyboardInterrupt

    monkeypatch.setattr(monitoring_runtime, "serve_forever", interrupt)
    assert monitoring_runtime.main([]) == 0
    assert closed == [True]
