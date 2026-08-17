"""Buyer acceptance for the authenticated target-state planner API."""

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
    AuthorizationError,
    KeyverseAuthorizationConfig,
    build_keyverse_authorization_config,
    verify_keyverse_bearer,
)
from ea_core_foundation.service import (
    BindAddress,
    PlannerRequestError,
    TargetStatePlanRequest,
    build_target_state_plan_reader,
    create_service_server,
    parse_target_state_request,
)

_VALID_TOKEN = (
    "eyJhbGciOiJSUzI1NiIsImtpZCI6ImZpeHR1cmUta2V5IiwidHlwIjoiSldUIn0."
    "eyJhdWQiOiJlbnRlcnByaXNlLWFyY2hpdGVjdHVyZS1jb3JlIiwiZXhwIjoyMDAw"
    "MDAwMDAwLCJpc3MiOiJodHRwczovL2lkLmV4YW1wbGUvcmVhbG1zL2N3bCIsInJv"
    "bGUiOiJlYV9yZWFkZXIiLCJzdWIiOiJ1c2VyLTEyMyIsInRlbmFudCI6IjAxOGY0"
    "N2IyLTkwNWEtN2IxNi1iZmQ0LTdlNGY1M2YxMGU5MSJ9."
    "FqnmfoMNoDMVx4_hyqN3hJHmBfK-V0gpNIPH5GH4qFh8zYTh1IStIGGEsi2ur8W6"
    "-LJwwmZpQV9PFQO1QrDeCCRX-xfvNM3jqLLYjMHQEyMUkCXJJsybx9fgRa5uYgyMq"
    "s_0RvW_jWI1cgwb4bAo90DHX4MgAq7Je9dcT9Ml4SO483GEytWmqocrYy-GC0ktj"
    "wWZkqR2aL4iCYsXjcCYoSSxAXCFLginaj_sTn-UdOltmKsEDXeEUL1ZcPIhX-Q4zS"
    "4iheg0B-9OK17x22uZnQqZR6lRSM9ieqQmm04qwwaRzw-g7ADLqqLuTbE4BOPiyVT"
    "Wg29enwRx5BwSs_5AvA"
)
_JWK = {
    "kty": "RSA",
    "kid": "fixture-key",
    "alg": "RS256",
    "use": "sig",
    "n": (
        "smAzYGFFnkYBmLS6sP2NsjmF8iOONQ2TA_M4ttrFnbn7aJ9Do3Q1-LLmlh1qcAos"
        "iZcJpg5OaxXxv3YZMbg1MvkBHbK2zCOAZqV0FLBinUpk-D_MHTkbmRdBmETipTT9"
        "eO6TKb38JOwF1uilDT0evb7_buX6aC6_BWhJ2ZH6c39XJku6atyawv7AkDRPiWNxae"
        "0PrD4drdRgtdVjSizWjXUlt_J3zOGey1enpN8aagTZt65fnjBdChuLtGCmYOKVFX1"
        "YVuy30wdbcDatF-4NM1Gk1cn85r3-80oLAt9HG6AS9GtuzPDAbZByi_i-83gKjbu8"
        "_sViPFtZGgzlpbq0ow"
    ),
    "e": "AQAB",
}


def _config() -> KeyverseAuthorizationConfig:
    """Return the closed Keyverse RP profile used by these tests."""

    return KeyverseAuthorizationConfig(
        issuer_uri="https://id.example/realms/cwl",
        audience="enterprise-architecture-core",
        jwks_url="https://id.example/realms/cwl/protocol/openid-connect/certs",
        tenant_claim="tenant",
        role_claim="role",
        allowed_roles=frozenset({"ea_reader", "ea_architect"}),
    )


def _b64url(value: bytes) -> str:
    """Encode test JWT bytes without padding."""

    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _unsigned_token(payload: dict[str, Any]) -> str:
    """Build a structurally valid token for claim tests with mocked signature."""

    header = {"alg": "RS256", "kid": "fixture-key", "typ": "JWT"}
    return ".".join(
        (
            _b64url(json.dumps(header, separators=(",", ":")).encode()),
            _b64url(json.dumps(payload, separators=(",", ":")).encode()),
            _b64url(b"test-signature"),
        )
    )


def _claims(**changes: Any) -> dict[str, Any]:
    """Return valid baseline claims with requested changes."""

    claims: dict[str, Any] = {
        "iss": "https://id.example/realms/cwl",
        "aud": "enterprise-architecture-core",
        "exp": 2_000_000_000,
        "sub": "user-123",
        "tenant": "018f47b2-905a-7b16-bfd4-7e4f53f10e91",
        "role": "ea_reader",
    }
    claims.update(changes)
    return claims


def _jwks_loader(url: str, issuer: str) -> dict[str, Any]:
    """Return one deterministic Keyverse signing key."""

    assert url == _config().jwks_url
    assert issuer == _config().issuer_uri
    return {"keys": [_JWK]}


def test_keyverse_configuration_is_fail_closed_and_explicit() -> None:
    """The protected planner cannot start from partial authorization config."""

    assert build_keyverse_authorization_config({}) is None
    config = build_keyverse_authorization_config(
        {
            "EA_OIDC_ISSUER": _config().issuer_uri,
            "EA_OIDC_AUDIENCE": _config().audience,
            "EA_OIDC_JWKS_URL": _config().jwks_url,
            "EA_TENANT_CLAIM": "tenant",
            "EA_ROLE_CLAIM": "role",
            "EA_READ_ROLES": "ea_reader,ea_architect",
        }
    )
    assert config == _config()


def test_real_rs256_fixture_verifies_and_binds_tenant_role() -> None:
    """A real RSA signature plus exact claims produces one authorization context."""

    context = verify_keyverse_bearer(
        f"Bearer {_VALID_TOKEN}",
        _config(),
        jwks_loader=_jwks_loader,
        now_epoch=1_800_000_000,
    )
    assert context.tenant_record_id == UUID("018f47b2-905a-7b16-bfd4-7e4f53f10e91")
    assert context.role_code == "ea_reader"
    assert context.subject_id == "user-123"


def test_bearer_verification_rejects_invalid_signature_and_claims() -> None:
    """Signature, issuer, audience, expiry, tenant, and role all fail closed."""

    with pytest.raises(AuthorizationError, match="signature"):
        verify_keyverse_bearer(
            f"Bearer {_VALID_TOKEN[:-1]}B",
            _config(),
            jwks_loader=_jwks_loader,
            now_epoch=1_800_000_000,
        )

    for claims, error_code in (
        (_claims(iss="https://evil.example"), "invalid_token"),
        (_claims(aud="other-service"), "invalid_token"),
        (_claims(exp=1_700_000_000), "invalid_token"),
        (_claims(tenant="not-a-uuid"), "invalid_token"),
        (_claims(role="billing_admin"), "forbidden"),
    ):
        with pytest.raises(AuthorizationError) as captured:
            verify_keyverse_bearer(
                f"Bearer {_unsigned_token(claims)}",
                _config(),
                jwks_loader=_jwks_loader,
                signature_verifier=lambda signing_input, signature, jwk: True,
                now_epoch=1_800_000_000,
            )
        assert captured.value.error_code == error_code


def test_target_state_request_requires_exact_bitemporal_query() -> None:
    """Buyer reads require explicit valid/system time and a bounded horizon."""

    request = parse_target_state_request(
        "/v1/technology-target-state-plans/"
        "0196f100-1111-7111-8111-111111111111"
        "?valid_at=2027-02-01T00%3A00%3A00Z"
        "&recorded_at=2027-02-01T00%3A00%3A00Z"
        "&planning_horizon_days=180"
    )
    assert request.technology_version_id == UUID(
        "0196f100-1111-7111-8111-111111111111"
    )
    assert request.planning_horizon_days == 180
    assert request.valid_at.isoformat() == "2027-02-01T00:00:00+00:00"

    for path in (
        "/v1/technology-target-state-plans/not-a-uuid?valid_at=x&recorded_at=x",
        "/v1/technology-target-state-plans/"
        "0196f100-1111-7111-8111-111111111111?valid_at=2027-02-01T00:00:00Z",
        "/v1/technology-target-state-plans/"
        "0196f100-1111-7111-8111-111111111111"
        "?valid_at=2027-02-01T00:00:00Z&recorded_at=2027-02-01T00:00:00Z"
        "&planning_horizon_days=3651",
    ):
        with pytest.raises(PlannerRequestError):
            parse_target_state_request(path)


def test_plan_reader_uses_runtime_role_without_exposing_dsn() -> None:
    """The service passes verified tenant context through the purpose-bound DB port."""

    calls: list[tuple[list[str], dict[str, Any]]] = []

    def runner(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        calls.append((command, kwargs))
        return subprocess.CompletedProcess(
            command,
            0,
            stdout='[{"recommended_action_code":"approve_target_state"}]\n',
            stderr="",
        )

    reader = build_target_state_plan_reader(
        "postgresql://ea_runtime:secret@db.example/ea_core",
        runner=runner,
        base_environment={},
    )
    context = verify_keyverse_bearer(
        f"Bearer {_unsigned_token(_claims())}",
        _config(),
        jwks_loader=_jwks_loader,
        signature_verifier=lambda signing_input, signature, jwk: True,
        now_epoch=1_800_000_000,
    )
    result = reader(
        context,
        TargetStatePlanRequest.from_values(
            "0196f100-1111-7111-8111-111111111111",
            "2027-02-01T00:00:00Z",
            "2027-02-01T00:00:00Z",
            180,
        ),
    )
    assert result[0]["recommended_action_code"] == "approve_target_state"
    command, kwargs = calls[0]
    assert all("secret" not in argument for argument in command)
    assert kwargs["env"]["PGPASSWORD"] == "secret"
    assert "read_technology_target_state_plan" in " ".join(command)


def _http_request(
    host: str,
    port: int,
    path: str,
    authorization: str | None,
) -> tuple[int, dict[str, Any]]:
    """Issue one planner request with an optional bearer header."""

    connection = HTTPConnection(host, port, timeout=2)
    headers = {} if authorization is None else {"Authorization": authorization}
    try:
        connection.request("GET", path, headers=headers)
        response = connection.getresponse()
        return response.status, json.loads(response.read().decode("utf-8"))
    finally:
        connection.close()


def test_http_planner_requires_authorization_and_returns_next_actions() -> None:
    """An authenticated reader gets decision evidence; anonymous traffic cannot."""

    request_path = (
        "/v1/technology-target-state-plans/"
        "0196f100-1111-7111-8111-111111111111"
        "?valid_at=2027-02-01T00%3A00%3A00Z"
        "&recorded_at=2027-02-01T00%3A00%3A00Z"
    )
    server = create_service_server(
        BindAddress("127.0.0.1", 0),
        authorization_config=_config(),
        jwks_loader=_jwks_loader,
        signature_verifier=lambda signing_input, signature, jwk: True,
        target_state_plan_reader=lambda context, request: [
            {
                "technology_version_id": str(request.technology_version_id),
                "decision_readiness_code": "target_state_pending_approval",
                "recommended_action_code": "approve_target_state",
            }
        ],
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address[:2]
    try:
        denied_status, denied = _http_request(host, port, request_path, None)
        ok_status, ok = _http_request(
            host,
            port,
            request_path,
            f"Bearer {_unsigned_token(_claims())}",
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert denied_status == 401
    assert denied["error_code"] == "authorization_required"
    assert ok_status == 200
    assert ok["decision_count"] == 1
    assert ok["decisions"][0]["recommended_action_code"] == "approve_target_state"
    assert ok["next_action"] == "approve_target_state"
