"""Authenticated runtime acceptance for starting scheduled transformations."""

from __future__ import annotations

import base64
import json
import threading
from http.client import HTTPConnection
from typing import Any

import pytest

from ea_core_foundation.authorization import KeyverseAuthorizationConfig
from ea_core_foundation.runtime import create_runtime_server
from ea_core_foundation.service import BindAddress, PlannerExecutionError

_TENANT_ID = "018f47b2-905a-7b16-bfd4-7e4f53f10e91"
_TRANSFORMATION_ID = "0196e010-1111-7111-8111-111111111191"
_DECISION_REQUEST_ID = "0196e090-1111-7111-8111-111111111191"
_EVIDENCE_ID = "0195d145-64e8-7f4f-8a23-a0cc784cbf10"
_HISTORY_ID = "0196e091-1111-7111-8111-111111111191"
_OUTBOX_ID = "0196e092-1111-7111-8111-111111111191"
_START_PATH = f"/v1/architecture-transformations/{_TRANSFORMATION_ID}/start"
_SCHEDULE_PATH = f"/v1/architecture-transformations/{_TRANSFORMATION_ID}/schedule"


def _config(
    roles: frozenset[str] = frozenset({"ea_transformation_starter"}),
) -> KeyverseAuthorizationConfig:
    """Return the dedicated Keyverse relying-party profile for start authority."""

    return KeyverseAuthorizationConfig(
        issuer_uri="https://id.example/realms/cwl",
        audience="enterprise-architecture-core",
        jwks_url="https://id.example/realms/cwl/protocol/openid-connect/certs",
        tenant_claim="tenant",
        role_claim="role",
        allowed_roles=roles,
    )


def _payload(**changes: object) -> dict[str, object]:
    """Return one valid transformation-start body with optional mutations."""

    payload: dict[str, object] = {
        "decision_request_id": _DECISION_REQUEST_ID,
        "effective_at": "2027-01-17T00:00:00Z",
        "decision_reason_text": "Begin the approved target-state execution.",
        "evidence_record_id": _EVIDENCE_ID,
    }
    payload.update(changes)
    return payload


def _receipt(**changes: object) -> dict[str, object]:
    """Return one valid immutable start receipt with optional mutations."""

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


def _b64url(value: bytes) -> str:
    """Encode deterministic JWT fixture bytes without padding."""

    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _token(role: str = "ea_transformation_starter") -> str:
    """Build a structurally valid JWT for signature-mocked HTTP acceptance."""

    header = {"alg": "RS256", "kid": "fixture-key", "typ": "JWT"}
    payload = {
        "iss": _config().issuer_uri,
        "aud": _config().audience,
        "exp": 2_000_000_000,
        "sub": "transformation-operator-123",
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
    path: str = _START_PATH,
) -> tuple[int, dict[str, Any]]:
    """Issue one JSON POST and return the response status and object."""

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
    """Start the runtime on an ephemeral loopback port."""

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


def test_http_start_is_purpose_authorized_and_actionable() -> None:
    """Only a starter can advance a governed scheduled transformation."""

    writes: list[str] = []

    def writer(context: Any, request: Any) -> dict[str, object]:
        del request
        writes.append(context.subject_id)
        return _receipt()

    server, thread, host, port = _start_server(
        start_authorization_config=_config(),
        jwks_loader=_jwks_loader,
        signature_verifier=lambda signing_input, signature, jwk: True,
        target_state_start_writer=writer,
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
    assert ok["transformation_state_code"] == "started"
    assert ok["next_action"] == "monitor_transformation"
    assert writes == ["transformation-operator-123"]


def test_http_start_replay_returns_200() -> None:
    """An exact replay is observable without presenting a new state transition."""

    server, thread, host, port = _start_server(
        start_authorization_config=_config(),
        jwks_loader=_jwks_loader,
        signature_verifier=lambda signing_input, signature, jwk: True,
        target_state_start_writer=lambda context, request: _receipt(replayed=True),
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
            "start_authorization_config": "not-a-config",
            "target_state_start_writer": "not-a-writer",
        },
    ],
)
def test_http_start_fails_closed_without_policy_and_writer(
    kwargs: dict[str, object],
) -> None:
    """Starting requires both purpose authorization and a command port."""

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
    assert body["error_code"] == "start_unavailable"


def test_http_start_rejects_invalid_request_before_write() -> None:
    """Malformed start meaning remains a 400 before command execution."""

    writes: list[str] = []

    def writer(context: Any, request: Any) -> dict[str, object]:
        del context, request
        writes.append("write")
        return {}

    server, thread, host, port = _start_server(
        start_authorization_config=_config(),
        jwks_loader=_jwks_loader,
        signature_verifier=lambda signing_input, signature, jwk: True,
        target_state_start_writer=writer,
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
    assert body["error_code"] == "invalid_start_request"
    assert writes == []


def test_http_start_returns_retriable_failure_when_writer_raises() -> None:
    """Database state conflicts remain non-success with an actionable retry path."""

    def failing_writer(context: Any, request: Any) -> dict[str, object]:
        del context, request
        raise PlannerExecutionError("conflict")

    server, thread, host, port = _start_server(
        start_authorization_config=_config(),
        jwks_loader=_jwks_loader,
        signature_verifier=lambda signing_input, signature, jwk: True,
        target_state_start_writer=failing_writer,
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
    assert body["error_code"] == "start_command_failed"
    assert "Refresh" in body["next_action"]


def test_non_start_post_preserves_schedule_routing() -> None:
    """The new start route cannot steal the existing schedule endpoint."""

    server, thread, host, port = _start_server()
    try:
        status, body = _post(
            host,
            port,
            {},
            authorization=None,
            path=_SCHEDULE_PATH,
        )
    finally:
        _stop_server(server, thread)

    assert status == 503
    assert body["error_code"] == "schedule_unavailable"
