"""RED buyer acceptance for authoritative target-state approval commands."""

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
    KeyverseAuthorizationConfig,
    build_keyverse_authorization_config,
)
from ea_core_foundation.service import (
    BindAddress,
    PlannerRequestError,
    TargetStateApprovalRequest,
    build_target_state_approval_writer,
    create_service_server,
    parse_target_state_approval_request,
)

_TENANT_ID = "018f47b2-905a-7b16-bfd4-7e4f53f10e91"
_TRANSFORMATION_ID = "0196e010-1111-7111-8111-111111111191"
_DECISION_REQUEST_ID = "0196e030-1111-7111-8111-111111111191"
_EVIDENCE_ID = "0195d145-64e8-7f4f-8a23-a0cc784cbf10"


def _config(roles: frozenset[str] = frozenset({"ea_architecture_approver"})) -> KeyverseAuthorizationConfig:
    """Return a closed Keyverse relying-party profile for approval tests."""

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
            "Architecture board approved the reviewed target state and remediation evidence."
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
    assert build_keyverse_authorization_config(
        environment,
        roles_environment_name="EA_APPROVAL_ROLES",
    ) == _config()


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

    for path, payload in (
        (
            "/v1/architecture-transformations/not-a-uuid/approval",
            _approval_payload(),
        ),
        (
            f"/v1/architecture-transformations/{_TRANSFORMATION_ID}/approval",
            _approval_payload(decision_request_id="00000000-0000-4000-8000-000000000000"),
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
            _approval_payload(decision_actor_ref="spoofed-actor"),
        ),
    ):
        with pytest.raises(PlannerRequestError):
            parse_target_state_approval_request(path, payload)


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
    request = TargetStateApprovalRequest.from_values(
        _TRANSFORMATION_ID,
        _DECISION_REQUEST_ID,
        "2027-01-15T00:00:00Z",
        "Architecture board approved the reviewed target state.",
        _EVIDENCE_ID,
    )
    from ea_core_foundation.authorization import AuthorizationContext

    receipt = writer(
        AuthorizationContext(
            tenant_record_id=UUID(_TENANT_ID),
            role_code="ea_architecture_approver",
            subject_id="architecture-board-user-123",
            issuer_uri="https://id.example/realms/cwl",
        ),
        request,
    )
    assert receipt["transformation_state_code"] == "approved"
    assert receipt["next_action"] == "schedule_transformation"
    command, kwargs = calls[0]
    assert all("secret" not in argument for argument in command)
    assert kwargs["env"]["PGPASSWORD"] == "secret"
    command_text = " ".join(command)
    assert "approve_target_state" in command_text
    assert "architecture-board-user-123" in command_text


def _post(
    host: str,
    port: int,
    payload: object,
    *,
    authorization: str | None,
    content_type: str = "application/json",
) -> tuple[int, dict[str, Any]]:
    """Issue one approval request against the bound test server."""

    body = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": content_type, "Content-Length": str(len(body))}
    if authorization is not None:
        headers["Authorization"] = authorization
    connection = HTTPConnection(host, port, timeout=2)
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


def test_http_approval_is_purpose_authorized_and_returns_idempotent_receipt() -> None:
    """Only an approver can turn the planner action into an auditable approved state."""

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

    server = create_service_server(
        BindAddress("127.0.0.1", 0),
        approval_authorization_config=_config(),
        jwks_loader=_jwks_loader,
        signature_verifier=lambda signing_input, signature, jwk: True,
        target_state_approval_writer=writer,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address[:2]
    try:
        anonymous_status, anonymous = _post(
            host,
            port,
            _approval_payload(),
            authorization=None,
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
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert anonymous_status == 401
    assert anonymous["error_code"] == "authorization_required"
    assert denied_status == 403
    assert denied["error_code"] == "forbidden"
    assert ok_status == 201
    assert ok["transformation_state_code"] == "approved"
    assert ok["next_action"] == "schedule_transformation"
    assert writes == [("architecture-board-user-123", _DECISION_REQUEST_ID)]
