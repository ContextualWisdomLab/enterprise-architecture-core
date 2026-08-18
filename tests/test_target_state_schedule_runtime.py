"""Runtime and fault-path acceptance for target-state scheduling."""

from __future__ import annotations

import base64
import json
import subprocess
import threading
from http.client import HTTPConnection
from types import SimpleNamespace
from typing import Any
from uuid import UUID

import pytest

import ea_core_foundation.runtime as runtime_module
from ea_core_foundation.authorization import (
    AuthorizationContext,
    KeyverseAuthorizationConfig,
)
from ea_core_foundation.runtime import (
    TargetStateScheduleRequest,
    build_target_state_schedule_writer,
    create_runtime_server,
    parse_target_state_schedule_request,
)
from ea_core_foundation.service import (
    BindAddress,
    PlannerExecutionError,
    PlannerRequestError,
)

_TENANT_ID = "018f47b2-905a-7b16-bfd4-7e4f53f10e91"
_TRANSFORMATION_ID = "0196e010-1111-7111-8111-111111111191"
_MILESTONE_ID = "0196e060-1111-7111-8111-111111111191"
_DECISION_REQUEST_ID = "0196e070-1111-7111-8111-111111111191"
_EVIDENCE_ID = "0195d145-64e8-7f4f-8a23-a0cc784cbf10"
_SCHEDULE_RECORD_ID = "0196e080-1111-7111-8111-111111111191"
_SCHEDULE_PATH = f"/v1/architecture-transformations/{_TRANSFORMATION_ID}/schedule"


def _config(
    roles: frozenset[str] = frozenset({"ea_transformation_scheduler"}),
) -> KeyverseAuthorizationConfig:
    """Return a closed Keyverse relying-party profile for scheduling."""
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


def _request() -> TargetStateScheduleRequest:
    """Return one valid immutable schedule decision."""
    return TargetStateScheduleRequest.from_values(
        _TRANSFORMATION_ID,
        _DECISION_REQUEST_ID,
        _MILESTONE_ID,
        "2027-01-16T00:00:00Z",
        "Bind the approved target state to the reviewed migration milestone.",
        _EVIDENCE_ID,
    )


def _payload(**changes: object) -> dict[str, object]:
    """Return one valid schedule JSON object with optional mutations."""
    payload: dict[str, object] = {
        "decision_request_id": _DECISION_REQUEST_ID,
        "initiative_milestone_id": _MILESTONE_ID,
        "effective_at": "2027-01-16T00:00:00Z",
        "decision_reason_text": (
            "Bind the approved target state to the migration milestone."
        ),
        "evidence_record_id": _EVIDENCE_ID,
    }
    payload.update(changes)
    return payload


def _valid_receipt(**changes: object) -> dict[str, object]:
    """Return one database-shaped schedule receipt with optional mutations."""
    receipt: dict[str, object] = {
        "transformation_schedule_record_id": _SCHEDULE_RECORD_ID,
        "architecture_transformation_id": _TRANSFORMATION_ID,
        "initiative_milestone_id": _MILESTONE_ID,
        "decision_request_id": _DECISION_REQUEST_ID,
        "milestone_target_at": "2027-03-31T00:00:00+00:00",
        "schedule_recorded_at": "2027-01-16T00:00:01+00:00",
        "replayed": False,
        "next_action": "start_transformation",
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


def _b64url(value: bytes) -> str:
    """Encode deterministic JWT fixture bytes without padding."""
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _token(role: str = "ea_transformation_scheduler") -> str:
    """Build a structurally valid JWT for signature-mocked HTTP acceptance."""
    header = {"alg": "RS256", "kid": "fixture-key", "typ": "JWT"}
    payload = {
        "iss": _config().issuer_uri,
        "aud": _config().audience,
        "exp": 2_000_000_000,
        "sub": "transformation-planner-123",
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
    """Return one signing key while asserting the Keyverse boundary."""
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
    path: str = _SCHEDULE_PATH,
) -> tuple[int, dict[str, Any]]:
    """Issue one schedule HTTP request and return its JSON response."""
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
    """Start the scheduling runtime on an ephemeral loopback port."""
    server = create_runtime_server(BindAddress("127.0.0.1", 0), **kwargs)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address[:2]
    return server, thread, host, port


def _stop_server(server: Any, thread: threading.Thread) -> None:
    """Release one in-process scheduling runtime."""
    server.shutdown()
    server.server_close()
    thread.join(timeout=2)


@pytest.mark.parametrize(
    ("path", "payload"),
    [
        (f"/wrong/{_TRANSFORMATION_ID}/schedule", _payload()),
        (
            "/v1/architecture-transformations/"
            f"{_TRANSFORMATION_ID}/nested/schedule",
            _payload(),
        ),
        ("/v1/architecture-transformations//schedule", _payload()),
        (f"{_SCHEDULE_PATH}#fragment", _payload()),
        (
            _SCHEDULE_PATH,
            _payload(
                evidence_record_id="00000000-0000-4000-8000-000000000000"
            ),
        ),
        (_SCHEDULE_PATH, _payload(decision_reason_text="x" * 4097)),
        (_SCHEDULE_PATH, _payload(effective_at=123)),
    ],
)
def test_schedule_parser_rejects_remaining_ambiguous_inputs(
    path: str,
    payload: dict[str, object],
) -> None:
    """Unbound routes, identifiers, reasons, and typed values fail closed."""
    with pytest.raises(PlannerRequestError):
        parse_target_state_schedule_request(path, payload)


def test_schedule_request_rejects_non_string_transformation_id() -> None:
    """Direct callers cannot bypass UUIDv7 parsing with Python values."""
    with pytest.raises(PlannerRequestError):
        TargetStateScheduleRequest.from_values(  # type: ignore[arg-type]
            None,
            _DECISION_REQUEST_ID,
            _MILESTONE_ID,
            "2027-01-16T00:00:00Z",
            "approved",
            _EVIDENCE_ID,
        )


def test_schedule_writer_rejects_unbounded_verified_actor_reference() -> None:
    """Verified identity data is bounded before reaching the audit function."""
    writer = build_target_state_schedule_writer(
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
        (_runner_for([]), "invalid schedule receipt"),
    ],
)
def test_schedule_writer_fails_closed_on_runtime_faults(
    runner: Any,
    message: str,
) -> None:
    """Command and decoding faults never masquerade as scheduling success."""
    writer = build_target_state_schedule_writer(
        "postgresql://ea_runtime@db.example/ea_core",
        runner=runner,
        base_environment={},
    )
    with pytest.raises(PlannerExecutionError, match=message):
        writer(_context(), _request())


@pytest.mark.parametrize(
    "changes",
    [
        {"transformation_schedule_record_id": "not-a-uuid"},
        {"milestone_target_at": "not-a-time"},
        {"schedule_recorded_at": "not-a-time"},
        {
            "architecture_transformation_id": (
                "0196e010-1111-7111-8111-111111111192"
            )
        },
        {"initiative_milestone_id": "0196e060-1111-7111-8111-111111111192"},
        {"decision_request_id": "0196e070-1111-7111-8111-111111111192"},
        {"replayed": "false"},
        {"next_action": "silently_mutate"},
    ],
)
def test_schedule_writer_rejects_receipt_drift(
    changes: dict[str, object],
) -> None:
    """A syntactically valid but different receipt fails closed."""
    writer = build_target_state_schedule_writer(
        "postgresql://ea_runtime@db.example/ea_core",
        runner=_runner_for(_valid_receipt(**changes)),
        base_environment={},
    )
    with pytest.raises(PlannerExecutionError, match="invalid schedule receipt"):
        writer(_context(), _request())


def test_http_schedule_is_purpose_authorized_and_actionable() -> None:
    """Only a scheduler can bind an approved transformation to a milestone."""
    writes: list[str] = []

    def writer(context: Any, request: Any) -> dict[str, object]:
        del request
        writes.append(context.subject_id)
        return _valid_receipt()

    server, thread, host, port = _start_server(
        schedule_authorization_config=_config(),
        jwks_loader=_jwks_loader,
        signature_verifier=lambda signing_input, signature, jwk: True,
        target_state_schedule_writer=writer,
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
    assert ok["next_action"] == "start_transformation"
    assert writes == ["transformation-planner-123"]


def test_http_schedule_replay_returns_200() -> None:
    """An exact replay is observable without presenting a new schedule."""
    server, thread, host, port = _start_server(
        schedule_authorization_config=_config(),
        jwks_loader=_jwks_loader,
        signature_verifier=lambda signing_input, signature, jwk: True,
        target_state_schedule_writer=lambda context, request: _valid_receipt(
            replayed=True
        ),
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
            "schedule_authorization_config": "not-a-config",
            "target_state_schedule_writer": "not-a-writer",
        },
    ],
)
def test_http_schedule_fails_closed_without_policy_and_writer(
    kwargs: dict[str, object],
) -> None:
    """Scheduling requires both authorization policy and command port."""
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
    assert body["error_code"] == "schedule_unavailable"


def test_http_schedule_rejects_invalid_request_before_write() -> None:
    """Malformed scheduling meaning remains a 400 before command execution."""
    writes: list[str] = []

    def writer(context: Any, request: Any) -> dict[str, object]:
        del context, request
        writes.append("write")
        return {}

    server, thread, host, port = _start_server(
        schedule_authorization_config=_config(),
        jwks_loader=_jwks_loader,
        signature_verifier=lambda signing_input, signature, jwk: True,
        target_state_schedule_writer=writer,
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
    assert body["error_code"] == "invalid_schedule_request"
    assert writes == []


def test_http_schedule_returns_retriable_failure_when_writer_raises() -> None:
    """Database conflicts remain non-success with an actionable retry path."""

    def failing_writer(context: Any, request: Any) -> dict[str, object]:
        del context, request
        raise PlannerExecutionError("conflict")

    server, thread, host, port = _start_server(
        schedule_authorization_config=_config(),
        jwks_loader=_jwks_loader,
        signature_verifier=lambda signing_input, signature, jwk: True,
        target_state_schedule_writer=failing_writer,
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
    assert body["error_code"] == "schedule_command_failed"
    assert "Refresh" in body["next_action"]


def test_non_schedule_post_preserves_inherited_handler_behavior() -> None:
    """Scheduling routing does not steal the existing approval endpoint."""
    approval_path = (
        f"/v1/architecture-transformations/{_TRANSFORMATION_ID}/approval"
    )
    server, thread, host, port = _start_server()
    try:
        status, body = _post(
            host,
            port,
            {},
            authorization=None,
            path=approval_path,
        )
    finally:
        _stop_server(server, thread)
    assert status == 503
    assert body["error_code"] == "approval_unavailable"


def _patch_runtime_main(monkeypatch, fake_server: Any, loop: Any) -> None:
    """Replace external runtime ports while preserving main orchestration."""
    monkeypatch.setattr(
        runtime_module,
        "resolve_bind_address",
        lambda environ: BindAddress("127.0.0.1", 0),
    )
    monkeypatch.setattr(runtime_module, "probe_context_contract", lambda: True)
    monkeypatch.setattr(
        runtime_module,
        "build_database_readiness_probe",
        lambda dsn: None,
    )
    monkeypatch.setattr(
        runtime_module,
        "build_keyverse_authorization_config",
        lambda env: None,
    )
    monkeypatch.setattr(
        runtime_module,
        "build_approval_authorization_config",
        lambda env: None,
    )
    monkeypatch.setattr(
        runtime_module,
        "build_schedule_authorization_config",
        lambda env: None,
    )
    monkeypatch.setattr(
        runtime_module,
        "build_target_state_plan_reader",
        lambda dsn: None,
    )
    monkeypatch.setattr(
        runtime_module,
        "build_target_state_approval_writer",
        lambda dsn: None,
    )
    monkeypatch.setattr(
        runtime_module,
        "build_target_state_schedule_writer",
        lambda dsn: None,
    )
    monkeypatch.setattr(
        runtime_module,
        "create_runtime_server",
        lambda *args, **kwargs: fake_server,
    )
    monkeypatch.setattr(runtime_module, "serve_forever", loop)


def test_runtime_main_closes_server_on_keyboard_interrupt(monkeypatch) -> None:
    """Operator interruption closes the listener and returns success."""
    closed: list[bool] = []
    fake_server = SimpleNamespace(server_close=lambda: closed.append(True))

    def interrupt(server: Any) -> None:
        del server
        raise KeyboardInterrupt

    _patch_runtime_main(monkeypatch, fake_server, interrupt)
    assert runtime_module.main([]) == 0
    assert closed == [True]


def test_runtime_main_returns_zero_when_server_loop_returns(monkeypatch) -> None:
    """A normally returning injected loop still closes its listener."""
    closed: list[bool] = []
    fake_server = SimpleNamespace(server_close=lambda: closed.append(True))
    _patch_runtime_main(monkeypatch, fake_server, lambda server: None)

    assert runtime_module.main([]) == 0
    assert closed == [True]
