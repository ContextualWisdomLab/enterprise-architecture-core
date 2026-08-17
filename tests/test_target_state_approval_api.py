"""Buyer acceptance for the governed target-state approval command."""

from __future__ import annotations

import base64
import json
import subprocess
import threading
from http.client import HTTPConnection
from typing import Any
from uuid import UUID

import pytest

from ea_core_foundation.authorization import (
    AuthorizationContext,
    KeyverseAuthorizationConfig,
    build_keyverse_authorization_config,
)
from ea_core_foundation.service import (
    BindAddress,
    PlannerExecutionError,
    PlannerRequestError,
    TargetStateApprovalRequest,
    build_approval_authorization_config,
    build_target_state_approval_writer,
    create_service_server,
    parse_target_state_approval_request,
)

_TENANT_ID = "018f47b2-905a-7b16-bfd4-7e4f53f10e91"
_TRANSFORMATION_ID = "0196e010-1111-7111-8111-111111111191"
_DECISION_REQUEST_ID = "0196e030-1111-7111-8111-111111111191"
_EVIDENCE_ID = "0195d145-64e8-7f4f-8a23-a0cc784cbf10"


def _config(
    roles: frozenset[str] = frozenset({"ea_architecture_approver"}),
) -> KeyverseAuthorizationConfig:
    """Return a closed Keyverse relying-party profile for approval tests."""

    return KeyverseAuthorizationConfig(
        issuer_uri="https://id.example/realms/cwl",
        audience="enterprise-architecture-core",
        jwks_url="https://id.example/realms/cwl/protocol/openid-connect/certs",
        tenant_claim="tenant",
        role_claim="role",
        allowed_roles=roles,
    )


def _authorization_context(
    subject: str = "architecture-board-user-123",
) -> AuthorizationContext:
    """Return one already-verified identity context for database-port tests."""

    return AuthorizationContext(
        tenant_record_id=UUID(_TENANT_ID),
        role_code="ea_architecture_approver",
        subject_id=subject,
        issuer_uri="https://id.example/realms/cwl",
    )


def _request() -> TargetStateApprovalRequest:
    """Return one exact immutable approval request."""

    return TargetStateApprovalRequest.from_values(
        _TRANSFORMATION_ID,
        _DECISION_REQUEST_ID,
        "2027-01-15T00:00:00Z",
        "Architecture board approved the reviewed target state.",
        _EVIDENCE_ID,
    )


def _b64url(value: bytes) -> str:
    """Encode deterministic JWT fixture bytes without padding."""

    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _token(role: str = "ea_architecture_approver") -> str:
    """Build a structurally valid JWT for signature-mocked HTTP tests."""

    header = {"alg": "RS256", "kid": "fixture-key", "typ": "JWT"}
    payload = {
        "iss": "https://id.example/realms/cwl",
        "aud": "enterprise-architecture-core",
        "exp": 2_000_000_000,
        "sub": "architecture-board-user-123",
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
    """Return one syntactically valid signing key for mocked signature tests."""

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


def _approval_payload(**changes: object) -> dict[str, object]:
    """Return one valid approval payload with optional mutations."""

    payload: dict[str, object] = {
        "decision_request_id": _DECISION_REQUEST_ID,
        "effective_at": "2027-01-15T00:00:00Z",
        "decision_reason_text": (
            "Architecture board approved the reviewed target state "
            "and remediation evidence."
        ),
        "evidence_record_id": _EVIDENCE_ID,
    }
    payload.update(changes)
    return payload


def test_approval_roles_are_configured_separately_from_read_roles() -> None:
    """A write decision must never inherit authorization merely from read access."""

    environment = {
        "EA_OIDC_ISSUER": _config().issuer_uri,
        "EA_OIDC_AUDIENCE": _config().audience,
        "EA_OIDC_JWKS_URL": _config().jwks_url,
        "EA_TENANT_CLAIM": "tenant",
        "EA_ROLE_CLAIM": "role",
        "EA_READ_ROLES": "ea_reader",
        "EA_APPROVAL_ROLES": "ea_architecture_approver",
    }
    assert build_keyverse_authorization_config(environment) == _config(
        frozenset({"ea_reader"})
    )
    assert build_approval_authorization_config(environment) == _config()
    assert build_approval_authorization_config(
        {key: value for key, value in environment.items() if key != "EA_APPROVAL_ROLES"}
    ) is None


def test_approval_request_requires_uuidv7_evidence_reason_and_aware_time() -> None:
    """Approval parsing rejects spoofed actors, ambiguous fields, and weak identifiers."""

    request = parse_target_state_approval_request(
        f"/v1/architecture-transformations/{_TRANSFORMATION_ID}/approval",
        _approval_payload(),
    )
    assert request.architecture_transformation_id == UUID(_TRANSFORMATION_ID)
    assert request.decision_request_id == UUID(_DECISION_REQUEST_ID)
    assert request.evidence_record_id == UUID(_EVIDENCE_ID)
    assert request.effective_at.isoformat() == "2027-01-15T00:00:00+00:00"

    invalid_cases = (
        (
            "/v1/architecture-transformations/not-a-uuid/approval",
            _approval_payload(),
        ),
        (
            f"/v1/architecture-transformations/{_TRANSFORMATION_ID}/approval?force=true",
            _approval_payload(),
        ),
        (
            f"/wrong/{_TRANSFORMATION_ID}/approval",
            _approval_payload(),
        ),
        (
            f"/v1/architecture-transformations/{_TRANSFORMATION_ID}/nested/approval",
            _approval_payload(),
        ),
        (
            f"/v1/architecture-transformations/{_TRANSFORMATION_ID}/approval",
            _approval_payload(decision_request_id="00000000-0000-4000-8000-000000000000"),
        ),
        (
            f"/v1/architecture-transformations/{_TRANSFORMATION_ID}/approval",
            _approval_payload(evidence_record_id="00000000-0000-4000-8000-000000000000"),
        ),
        (
            f"/v1/architecture-transformations/{_TRANSFORMATION_ID}/approval",
            _approval_payload(effective_at="not-a-time"),
        ),
        (
            f"/v1/architecture-transformations/{_TRANSFORMATION_ID}/approval",
            _approval_payload(effective_at="2027-01-15T00:00:00"),
        ),
        (
            f"/v1/architecture-transformations/{_TRANSFORMATION_ID}/approval",
            _approval_payload(decision_reason_text=" "),
        ),
        (
            f"/v1/architecture-transformations/{_TRANSFORMATION_ID}/approval",
            _approval_payload(decision_reason_text="x" * 4097),
        ),
        (
            f"/v1/architecture-transformations/{_TRANSFORMATION_ID}/approval",
            _approval_payload(decision_actor_ref="spoofed-actor"),
        ),
        (
            f"/v1/architecture-transformations/{_TRANSFORMATION_ID}/approval",
            _approval_payload(effective_at=123),
        ),
    )
    for path, payload in invalid_cases:
        with pytest.raises(PlannerRequestError):
            parse_target_state_approval_request(path, payload)

    with pytest.raises(PlannerRequestError):
        TargetStateApprovalRequest.from_values(  # type: ignore[arg-type]
            None,
            _DECISION_REQUEST_ID,
            "2027-01-15T00:00:00Z",
            "approved",
            _EVIDENCE_ID,
        )


def test_approval_writer_binds_verified_actor_without_exposing_database_secret() -> None:
    """The runtime writer uses the narrow DB port and derives actor from verified identity."""

    calls: list[tuple[list[str], dict[str, Any]]] = []

    def runner(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        calls.append((command, kwargs))
        return subprocess.CompletedProcess(
            command,
            0,
            stdout=(
                '{"transformation_history_record_id":"0196e040-1111-7111-8111-111111111191",'
                '"transformation_state_code":"approved",'
                '"outbox_event_id":"0196e050-1111-7111-8111-111111111191",'
                '"decision_request_id":"0196e030-1111-7111-8111-111111111191",'
                '"replayed":false,"next_action":"schedule_transformation"}\n'
            ),
            stderr="",
        )

    writer = build_target_state_approval_writer(
        "postgresql://ea_runtime:secret@db.example/ea_core",
        runner=runner,
        base_environment={},
    )
    receipt = writer(_authorization_context(), _request())
    assert receipt["transformation_state_code"] == "approved"
    assert receipt["next_action"] == "schedule_transformation"
    command, kwargs = calls[0]
    assert all("secret" not in argument for argument in command)
    assert kwargs["env"]["PGPASSWORD"] == "secret"
    command_text = " ".join(command)
    assert "approve_target_state" in command_text
    assert "architecture-board-user-123" in command_text


@pytest.mark.parametrize("dsn", [None, "http://not-postgres.example/db"])
def test_approval_writer_fails_closed_without_a_safe_database_dsn(dsn: str | None) -> None:
    """No DSN or a non-PostgreSQL DSN cannot become write authority."""

    writer = build_target_state_approval_writer(dsn, base_environment={})
    with pytest.raises(PlannerExecutionError, match="unavailable"):
        writer(_authorization_context(), _request())


def test_approval_writer_rejects_unbounded_verified_actor_reference() -> None:
    """Even verified identity data is bounded before it reaches the audit store."""

    writer = build_target_state_approval_writer(
        "postgresql://ea_runtime@db.example/ea_core",
        runner=lambda command, **kwargs: pytest.fail("runner should not execute"),
        base_environment={},
    )
    with pytest.raises(PlannerExecutionError, match="actor reference"):
        writer(_authorization_context("x" * 3000), _request())


@pytest.mark.parametrize(
    ("runner", "message"),
    [
        (
            lambda command, **kwargs: (_ for _ in ()).throw(OSError("psql missing")),
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
        (
            lambda command, **kwargs: subprocess.CompletedProcess(
                command, 0, stdout="[]", stderr=""
            ),
            "invalid decision receipt",
        ),
        (
            lambda command, **kwargs: subprocess.CompletedProcess(
                command,
                0,
                stdout=json.dumps(
                    {
                        "transformation_state_code": "proposed",
                        "replayed": False,
                        "next_action": "schedule_transformation",
                    }
                ),
                stderr="",
            ),
            "invalid decision receipt",
        ),
        (
            lambda command, **kwargs: subprocess.CompletedProcess(
                command,
                0,
                stdout=json.dumps(
                    {
                        "transformation_state_code": "approved",
                        "replayed": "false",
                        "next_action": "schedule_transformation",
                    }
                ),
                stderr="",
            ),
            "invalid decision receipt",
        ),
    ],
)
def test_approval_writer_fails_closed_on_runtime_or_receipt_faults(
    runner: Any,
    message: str,
) -> None:
    """A failed command or malformed DB receipt can never masquerade as approval."""

    writer = build_target_state_approval_writer(
        "postgresql://ea_runtime@db.example/ea_core",
        runner=runner,
        base_environment={},
    )
    with pytest.raises(PlannerExecutionError, match=message):
        writer(_authorization_context(), _request())


def _http_request(
    host: str,
    port: int,
    body: bytes,
    *,
    authorization: str | None,
    content_type: str = "application/json",
    content_length: str | None = None,
) -> tuple[int, dict[str, Any]]:
    """Issue one raw-enough approval request to exercise hostile HTTP input."""

    connection = HTTPConnection(host, port, timeout=2)
    headers = {"Content-Type": content_type}
    if authorization is not None:
        headers["Authorization"] = authorization
    if content_length is not None:
        headers["Content-Length"] = content_length
    try:
        connection.request(
            "POST",
            f"/v1/architecture-transformations/{_TRANSFORMATION_ID}/approval",
            body=body,
            headers=headers,
        )
        response = connection.getresponse()
        return response.status, json.loads(response.read().decode("utf-8"))
    finally:
        connection.close()


def _post(
    host: str,
    port: int,
    payload: object,
    *,
    authorization: str | None,
    content_type: str = "application/json",
) -> tuple[int, dict[str, Any]]:
    """Issue one normal JSON approval request."""

    body = json.dumps(payload).encode("utf-8")
    return _http_request(
        host,
        port,
        body,
        authorization=authorization,
        content_type=content_type,
        content_length=str(len(body)),
    )


def _start_server(**kwargs: Any) -> tuple[Any, threading.Thread, str, int]:
    """Start one in-process service instance and return its bound endpoint."""

    server = create_service_server(BindAddress("127.0.0.1", 0), **kwargs)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address[:2]
    return server, thread, host, port


def _stop_server(server: Any, thread: threading.Thread) -> None:
    """Release one in-process service instance."""

    server.shutdown()
    server.server_close()
    thread.join(timeout=2)


def test_http_approval_is_purpose_authorized_and_returns_actionable_receipt() -> None:
    """Only an approver can turn planner advice into an auditable approved state."""

    writes: list[tuple[str, str]] = []

    def writer(context: Any, request: TargetStateApprovalRequest) -> dict[str, object]:
        writes.append((context.subject_id, str(request.decision_request_id)))
        return {
            "transformation_history_record_id": "0196e040-1111-7111-8111-111111111191",
            "transformation_state_code": "approved",
            "outbox_event_id": "0196e050-1111-7111-8111-111111111191",
            "decision_request_id": _DECISION_REQUEST_ID,
            "replayed": False,
            "next_action": "schedule_transformation",
        }

    server, thread, host, port = _start_server(
        approval_authorization_config=_config(),
        jwks_loader=_jwks_loader,
        signature_verifier=lambda signing_input, signature, jwk: True,
        target_state_approval_writer=writer,
    )
    try:
        anonymous_status, anonymous = _post(
            host, port, _approval_payload(), authorization=None
        )
        denied_status, denied = _post(
            host,
            port,
            _approval_payload(),
            authorization=f"Bearer {_token('ea_reader')}",
        )
        ok_status, ok = _post(
            host,
            port,
            _approval_payload(),
            authorization=f"Bearer {_token()}",
        )
    finally:
        _stop_server(server, thread)

    assert anonymous_status == 401
    assert anonymous["error_code"] == "authorization_required"
    assert denied_status == 403
    assert denied["error_code"] == "forbidden"
    assert ok_status == 201
    assert ok["transformation_state_code"] == "approved"
    assert ok["next_action"] == "schedule_transformation"
    assert writes == [("architecture-board-user-123", _DECISION_REQUEST_ID)]


def test_http_approval_replay_returns_200_without_reframing_the_decision() -> None:
    """An exact idempotent replay is observable but is not presented as a new approval."""

    server, thread, host, port = _start_server(
        approval_authorization_config=_config(),
        jwks_loader=_jwks_loader,
        signature_verifier=lambda signing_input, signature, jwk: True,
        target_state_approval_writer=lambda context, request: {
            "transformation_history_record_id": "0196e040-1111-7111-8111-111111111191",
            "transformation_state_code": "approved",
            "outbox_event_id": "0196e050-1111-7111-8111-111111111191",
            "decision_request_id": _DECISION_REQUEST_ID,
            "replayed": True,
            "next_action": "schedule_transformation",
        },
    )
    try:
        status, body = _post(
            host,
            port,
            _approval_payload(),
            authorization=f"Bearer {_token()}",
        )
    finally:
        _stop_server(server, thread)
    assert status == 200
    assert body["replayed"] is True


def test_http_approval_fails_closed_when_configuration_or_writer_is_missing() -> None:
    """An endpoint without both approval policy and command port remains unavailable."""

    for kwargs in (
        {},
        {
            "approval_authorization_config": "not-a-config",
            "target_state_approval_writer": "not-a-writer",
        },
    ):
        server, thread, host, port = _start_server(**kwargs)
        try:
            status, body = _post(
                host,
                port,
                _approval_payload(),
                authorization=f"Bearer {_token()}",
            )
        finally:
            _stop_server(server, thread)
        assert status == 503
        assert body["error_code"] == "approval_unavailable"


def test_http_approval_rejects_malformed_or_hostile_bodies_before_write() -> None:
    """Media type, size, Unicode, JSON shape, duplicates, and actor spoofing fail closed."""

    writes: list[str] = []
    server, thread, host, port = _start_server(
        approval_authorization_config=_config(),
        jwks_loader=_jwks_loader,
        signature_verifier=lambda signing_input, signature, jwk: True,
        target_state_approval_writer=lambda context, request: writes.append("write") or {},
    )
    authorization = f"Bearer {_token()}"
    hostile_requests = (
        (b"{}", "text/plain", "2"),
        (b"{}", "application/json", "0"),
        (b"{}", "application/json", "20000"),
        (b"\xff", "application/json", "1"),
        (b"[]", "application/json", "2"),
        (
            (
                '{"decision_request_id":"%s","decision_request_id":"%s"}'
                % (_DECISION_REQUEST_ID, _DECISION_REQUEST_ID)
            ).encode(),
            "application/json",
            None,
        ),
        (
            json.dumps(_approval_payload(decision_actor_ref="spoof")).encode(),
            "application/json",
            None,
        ),
    )
    try:
        for body, content_type, explicit_length in hostile_requests:
            length = str(len(body)) if explicit_length is None else explicit_length
            status, response = _http_request(
                host,
                port,
                body,
                authorization=authorization,
                content_type=content_type,
                content_length=length,
            )
            assert status == 400
            assert response["error_code"] == "invalid_approval_request"
    finally:
        _stop_server(server, thread)
    assert writes == []


def test_http_approval_rejects_invalid_content_length_without_reading_a_body() -> None:
    """A malformed length header cannot force unbounded or ambiguous body reads."""

    server, thread, host, port = _start_server(
        approval_authorization_config=_config(),
        jwks_loader=_jwks_loader,
        signature_verifier=lambda signing_input, signature, jwk: True,
        target_state_approval_writer=lambda context, request: {},
    )
    connection = HTTPConnection(host, port, timeout=2)
    try:
        connection.putrequest(
            "POST", f"/v1/architecture-transformations/{_TRANSFORMATION_ID}/approval"
        )
        connection.putheader("Content-Type", "application/json")
        connection.putheader("Content-Length", "not-an-integer")
        connection.putheader("Authorization", f"Bearer {_token()}")
        connection.endheaders()
        response = connection.getresponse()
        body = json.loads(response.read().decode())
        assert response.status == 400
        assert body["error_code"] == "invalid_approval_request"
    finally:
        connection.close()
        _stop_server(server, thread)


def test_http_approval_returns_retriable_failure_when_command_port_raises() -> None:
    """Database/state conflicts remain non-success and instruct the buyer to refresh."""

    def failing_writer(context: Any, request: Any) -> dict[str, object]:
        raise PlannerExecutionError("conflict")

    server, thread, host, port = _start_server(
        approval_authorization_config=_config(),
        jwks_loader=_jwks_loader,
        signature_verifier=lambda signing_input, signature, jwk: True,
        target_state_approval_writer=failing_writer,
    )
    try:
        status, body = _post(
            host,
            port,
            _approval_payload(),
            authorization=f"Bearer {_token()}",
        )
    finally:
        _stop_server(server, thread)
    assert status == 503
    assert body["error_code"] == "approval_command_failed"
    assert "Refresh" in body["next_action"]
