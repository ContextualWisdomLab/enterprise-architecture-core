"""Authenticated runtime acceptance for completed target-state verification."""

from __future__ import annotations

import base64
import json
import threading
from http.client import HTTPConnection
from types import SimpleNamespace
from typing import Any

import pytest

import ea_core_foundation.verification_runtime as verification_runtime
from ea_core_foundation.authorization import KeyverseAuthorizationConfig
from ea_core_foundation.service import BindAddress, PlannerExecutionError
from ea_core_foundation.verification_runtime import create_runtime_server

_TENANT_ID = "018f47b2-905a-7b16-bfd4-7e4f53f10e91"
_TRANSFORMATION_ID = "0196e010-1111-7111-8111-111111111191"
_DECISION_REQUEST_ID = "0196e0a0-1111-7111-8111-111111111193"
_EVIDENCE_ID = "0195d145-64e8-7f4f-8a23-a0cc784cbf10"
_HISTORY_ID = "0196e0a1-1111-7111-8111-111111111193"
_OUTBOX_ID = "0196e0a2-1111-7111-8111-111111111193"
_VERIFY_PATH = f"/v1/architecture-transformations/{_TRANSFORMATION_ID}/verification"
_COMPLETE_PATH = f"/v1/architecture-transformations/{_TRANSFORMATION_ID}/complete"


def _config(
    roles: frozenset[str] = frozenset({"ea_target_state_verifier"}),
) -> KeyverseAuthorizationConfig:
    """Return the dedicated Keyverse relying-party profile for verification."""

    return KeyverseAuthorizationConfig(
        issuer_uri="https://id.example/realms/cwl",
        audience="enterprise-architecture-core",
        jwks_url="https://id.example/realms/cwl/protocol/openid-connect/certs",
        tenant_claim="tenant",
        role_claim="role",
        allowed_roles=roles,
    )


def _payload(**changes: object) -> dict[str, object]:
    """Return one valid verification body with optional mutations."""

    payload: dict[str, object] = {
        "decision_request_id": _DECISION_REQUEST_ID,
        "effective_at": "2027-02-02T00:00:00Z",
        "decision_reason_text": "Evidence confirms the approved target state.",
        "evidence_record_id": _EVIDENCE_ID,
        "verification_outcome_code": "verified",
    }
    payload.update(changes)
    return payload


def _receipt(**changes: object) -> dict[str, object]:
    """Return one valid immutable verification receipt with optional changes."""

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


def _b64url(value: bytes) -> str:
    """Encode deterministic JWT fixture bytes without padding."""

    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _token(role: str = "ea_target_state_verifier") -> str:
    """Build a structurally valid JWT for signature-mocked HTTP acceptance."""

    header = {"alg": "RS256", "kid": "fixture-key", "typ": "JWT"}
    payload = {
        "iss": _config().issuer_uri,
        "aud": _config().audience,
        "exp": 2_000_000_000,
        "sub": "target-state-verifier-123",
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
    path: str = _VERIFY_PATH,
) -> tuple[int, dict[str, Any]]:
    """Issue one JSON POST and return its status and response object."""

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
    """Start the verification-aware runtime on an ephemeral loopback port."""

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


def test_http_verification_is_purpose_authorized_and_actionable() -> None:
    """Only a verifier can record achieved target-state evidence."""

    writes: list[str] = []

    def writer(context: Any, request: Any) -> dict[str, object]:
        writes.append(f"{context.subject_id}:{request.verification_outcome_code}")
        return _receipt()

    server, thread, host, port = _start_server(
        verification_authorization_config=_config(),
        jwks_loader=_jwks_loader,
        signature_verifier=lambda signing_input, signature, jwk: True,
        target_state_verification_writer=writer,
    )
    try:
        anonymous_status, anonymous = _post(
            host, port, _payload(), authorization=None
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
    assert ok["verification_outcome_code"] == "verified"
    assert ok["next_action"] == "monitor_target_state"
    assert writes == ["target-state-verifier-123:verified"]


def test_http_verification_gap_and_replay_are_explicit() -> None:
    """Gap outcomes and exact replay preserve different actionable semantics."""

    server, thread, host, port = _start_server(
        verification_authorization_config=_config(),
        jwks_loader=_jwks_loader,
        signature_verifier=lambda signing_input, signature, jwk: True,
        target_state_verification_writer=lambda context, request: _receipt(
            verification_outcome_code=request.verification_outcome_code,
            replayed=True,
            next_action="replan_target_state",
        ),
    )
    try:
        status, body = _post(
            host,
            port,
            _payload(verification_outcome_code="gap_detected"),
            authorization=f"Bearer {_token()}",
        )
    finally:
        _stop_server(server, thread)

    assert status == 200
    assert body["verification_outcome_code"] == "gap_detected"
    assert body["next_action"] == "replan_target_state"


@pytest.mark.parametrize(
    "kwargs",
    [
        {},
        {
            "verification_authorization_config": "not-a-config",
            "target_state_verification_writer": "not-a-writer",
        },
    ],
)
def test_http_verification_fails_closed_without_policy_and_writer(
    kwargs: dict[str, object],
) -> None:
    """Verification requires both purpose authorization and a command port."""

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
    assert body["error_code"] == "verification_unavailable"


def test_http_verification_rejects_invalid_request_before_write() -> None:
    """Malformed verification meaning stays a 400 before command execution."""

    writes: list[str] = []

    def writer(context: Any, request: Any) -> dict[str, object]:
        del context, request
        writes.append("write")
        return {}

    server, thread, host, port = _start_server(
        verification_authorization_config=_config(),
        jwks_loader=_jwks_loader,
        signature_verifier=lambda signing_input, signature, jwk: True,
        target_state_verification_writer=writer,
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
    assert body["error_code"] == "invalid_verification_request"
    assert writes == []


def test_http_verification_returns_retriable_failure_when_writer_raises() -> None:
    """Database state conflicts remain non-success with an actionable retry path."""

    def failing_writer(context: Any, request: Any) -> dict[str, object]:
        del context, request
        raise PlannerExecutionError("conflict")

    server, thread, host, port = _start_server(
        verification_authorization_config=_config(),
        jwks_loader=_jwks_loader,
        signature_verifier=lambda signing_input, signature, jwk: True,
        target_state_verification_writer=failing_writer,
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
    assert body["error_code"] == "verification_command_failed"
    assert "Refresh" in body["next_action"]


def test_non_verification_post_preserves_completion_routing() -> None:
    """Verification cannot steal the existing completion endpoint."""

    server, thread, host, port = _start_server()
    try:
        status, body = _post(
            host,
            port,
            {},
            authorization=None,
            path=_COMPLETE_PATH,
        )
    finally:
        _stop_server(server, thread)

    assert status == 503
    assert body["error_code"] == "completion_unavailable"


def _patch_main_builders(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    """Replace startup dependencies while retaining complete verification wiring."""

    server = SimpleNamespace(server_close=lambda: None)
    monkeypatch.setattr(
        verification_runtime,
        "resolve_bind_address",
        lambda environ: BindAddress("127.0.0.1", 8080),
    )
    monkeypatch.setattr(verification_runtime, "probe_context_contract", lambda: True)
    monkeypatch.setattr(
        verification_runtime,
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
        "build_target_state_plan_reader",
        "build_target_state_approval_writer",
        "build_target_state_schedule_writer",
        "build_target_state_start_writer",
        "build_target_state_complete_writer",
        "build_target_state_verification_writer",
    ):
        monkeypatch.setattr(verification_runtime, name, lambda value, name=name: name)
    monkeypatch.setattr(
        verification_runtime,
        "create_runtime_server",
        lambda bind_address, **kwargs: server,
    )
    return server


def test_main_closes_runtime_after_exit_or_interrupt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Normal and operator shutdown both release the verification runtime."""

    server = _patch_main_builders(monkeypatch)
    closed: list[bool] = []
    server.server_close = lambda: closed.append(True)
    monkeypatch.setattr(verification_runtime, "serve_forever", lambda current: None)
    assert verification_runtime.main([]) == 0
    assert closed == [True]

    closed.clear()

    def interrupt(current: object) -> None:
        del current
        raise KeyboardInterrupt

    monkeypatch.setattr(verification_runtime, "serve_forever", interrupt)
    assert verification_runtime.main([]) == 0
    assert closed == [True]
