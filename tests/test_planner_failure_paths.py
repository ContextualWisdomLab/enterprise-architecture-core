"""Failure-path tests for the target-state planner service boundary."""

from __future__ import annotations

import base64
import json
import subprocess
import threading
from http.client import HTTPConnection
from typing import Any
from uuid import UUID

import pytest

import ea_core_foundation.service as service
from ea_core_foundation.authorization import (
    AuthorizationContext,
    KeyverseAuthorizationConfig,
)

_TECHNOLOGY = "0196f100-1111-7111-8111-111111111111"
_TENANT = UUID("018f47b2-905a-7b16-bfd4-7e4f53f10e91")


def _request() -> service.TargetStatePlanRequest:
    """Return one valid planner request used by database failure tests."""

    return service.TargetStatePlanRequest.from_values(
        _TECHNOLOGY,
        "2027-02-01T00:00:00Z",
        "2027-02-01T00:00:00Z",
        180,
    )


def _context() -> AuthorizationContext:
    """Return one already verified service authorization context."""

    return AuthorizationContext(
        tenant_record_id=_TENANT,
        role_code="ea_reader",
        subject_id="reader-1",
        issuer_uri="https://id.example/realms/cwl",
    )


def _b64url(value: bytes) -> str:
    """Encode a JWT test segment without padding."""

    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _token() -> str:
    """Build a claim-valid JWT-shaped value for injected signature verification."""

    header = {"alg": "RS256", "kid": "key-1", "typ": "JWT"}
    claims = {
        "iss": "https://id.example/realms/cwl",
        "aud": "enterprise-architecture-core",
        "exp": 2_000_000_000,
        "sub": "reader-1",
        "tenant": str(_TENANT),
        "role": "ea_reader",
    }
    return ".".join(
        (
            _b64url(json.dumps(header, separators=(",", ":")).encode()),
            _b64url(json.dumps(claims, separators=(",", ":")).encode()),
            _b64url(b"signature"),
        )
    )


def _config() -> KeyverseAuthorizationConfig:
    """Return the exact Keyverse profile used by HTTP failure tests."""

    return KeyverseAuthorizationConfig(
        issuer_uri="https://id.example/realms/cwl",
        audience="enterprise-architecture-core",
        jwks_url=(
            "https://id.example/realms/cwl/protocol/openid-connect/certs"
        ),
        tenant_claim="tenant",
        role_claim="role",
        allowed_roles=frozenset({"ea_reader"}),
    )


@pytest.mark.parametrize(
    "path",
    [
        "/wrong/path",
        "/v1/technology-target-state-plans/",
        f"/v1/technology-target-state-plans/{_TECHNOLOGY}/child"
        "?valid_at=2027-02-01T00:00:00Z&recorded_at=2027-02-01T00:00:00Z",
        f"/v1/technology-target-state-plans/{_TECHNOLOGY}"
        "?valid_at=2027-02-01T00:00:00Z&recorded_at=2027-02-01T00:00:00Z"
        "&unknown=value",
        f"/v1/technology-target-state-plans/{_TECHNOLOGY}"
        "?valid_at=2027-02-01T00:00:00Z&valid_at=2027-02-02T00:00:00Z"
        "&recorded_at=2027-02-01T00:00:00Z",
        f"/v1/technology-target-state-plans/{_TECHNOLOGY}"
        "?valid_at=2027-02-01T00:00:00Z&recorded_at=2027-02-01T00:00:00Z"
        "&planning_horizon_days=days",
    ],
)
def test_planner_parser_rejects_path_and_query_ambiguity(path: str) -> None:
    """Unknown paths, duplicate fields, and nonnumeric horizons fail closed."""

    with pytest.raises(service.PlannerRequestError):
        service.parse_target_state_request(path)


@pytest.mark.parametrize(
    "timestamp",
    ["not-a-time", "2027-02-01T00:00:00"],
)
def test_planner_request_requires_parseable_offset_time(timestamp: str) -> None:
    """Valid-time and system-time cutoffs cannot silently use local/naive time."""

    with pytest.raises(service.PlannerRequestError):
        service.TargetStatePlanRequest.from_values(
            _TECHNOLOGY,
            timestamp,
            "2027-02-01T00:00:00Z",
        )


def test_unavailable_or_malformed_database_dsn_returns_closed_reader() -> None:
    """No DB configuration path ever falls back to direct application-table SQL."""

    for dsn in (None, "not-postgresql://db"):
        reader = service.build_target_state_plan_reader(dsn)
        with pytest.raises(service.PlannerExecutionError, match="unavailable"):
            reader(_context(), _request())


def test_plan_reader_rejects_command_and_response_failures() -> None:
    """OS, psql, JSON, and response-shape failures all keep decisions pending."""

    cases: list[tuple[Any, str]] = []

    def os_failure(*args: Any, **kwargs: Any) -> Any:
        raise OSError("psql missing")

    def timeout_failure(*args: Any, **kwargs: Any) -> Any:
        raise subprocess.TimeoutExpired("psql", 10)

    def nonzero(
        command: list[str], **kwargs: Any
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, 2, "", "db error")

    def invalid_json(
        command: list[str], **kwargs: Any
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, 0, "not-json", "")

    def non_list(
        command: list[str], **kwargs: Any
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, 0, '{"row":1}', "")

    def bad_member(
        command: list[str], **kwargs: Any
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, 0, '["row"]', "")

    cases.extend(
        [
            (os_failure, "command failed"),
            (timeout_failure, "command failed"),
            (nonzero, "query failed"),
            (invalid_json, "invalid JSON"),
            (non_list, "invalid decision collection"),
            (bad_member, "invalid decision collection"),
        ]
    )
    for runner, message in cases:
        reader = service.build_target_state_plan_reader(
            "postgresql://ea_runtime:secret@db.example/ea_core",
            runner=runner,
            base_environment={},
        )
        with pytest.raises(service.PlannerExecutionError, match=message):
            reader(_context(), _request())


def test_readiness_probe_exception_fails_closed() -> None:
    """Probe bugs never turn a dependency into a passing readiness signal."""

    def broken_probe() -> bool:
        raise RuntimeError("probe bug")

    report = service.build_readiness_report(
        contract_ready=True,
        database_probe=broken_probe,
    )
    assert report.database_ready is False
    assert report.http_status() == 503


def _http(
    server: Any,
    path: str,
    *,
    authorization: str | None = None,
) -> tuple[int, dict[str, Any]]:
    """Issue one in-process HTTP request and decode its safe JSON response."""

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address[:2]
    connection = HTTPConnection(host, port, timeout=2)
    headers = {} if authorization is None else {"Authorization": authorization}
    try:
        connection.request("GET", path, headers=headers)
        response = connection.getresponse()
        return response.status, json.loads(response.read().decode())
    finally:
        connection.close()
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_http_planner_is_unavailable_without_complete_runtime_boundary() -> None:
    """Missing authorization configuration or a callable reader returns 503."""

    server = service.create_service_server(service.BindAddress("127.0.0.1", 0))
    status, body = _http(
        server,
        f"/v1/technology-target-state-plans/{_TECHNOLOGY}",
    )
    assert status == 503
    assert body["error_code"] == "planner_unavailable"

    server = service.create_service_server(
        service.BindAddress("127.0.0.1", 0),
        authorization_config=_config(),
        target_state_plan_reader=lambda context, request: [],
    )
    server.target_state_plan_reader = "not-callable"
    status, body = _http(
        server,
        f"/v1/technology-target-state-plans/{_TECHNOLOGY}",
    )
    assert status == 503
    assert body["error_code"] == "planner_unavailable"


def _authorized_server(reader: Any) -> Any:
    """Build a server whose cryptography is injected so routing can be isolated."""

    return service.create_service_server(
        service.BindAddress("127.0.0.1", 0),
        authorization_config=_config(),
        jwks_loader=lambda url, issuer: {
            "keys": [{"kid": "key-1", "kty": "RSA", "alg": "RS256"}]
        },
        signature_verifier=lambda signing_input, signature, jwk: True,
        target_state_plan_reader=reader,
    )


def test_http_planner_rejects_malformed_request_after_authorization() -> None:
    """Authenticated callers still need exact bitemporal request evidence."""

    server = _authorized_server(lambda context, request: [])
    status, body = _http(
        server,
        f"/v1/technology-target-state-plans/{_TECHNOLOGY}?valid_at=bad",
        authorization=f"Bearer {_token()}",
    )
    assert status == 400
    assert body["error_code"] == "invalid_planner_request"


def test_http_planner_query_failure_returns_safe_retry_action() -> None:
    """Database exceptions do not leak SQL, credentials, or token material."""

    def broken_reader(context: Any, request: Any) -> Any:
        raise RuntimeError("postgresql://user:secret@db/internal sql")

    server = _authorized_server(broken_reader)
    path = (
        f"/v1/technology-target-state-plans/{_TECHNOLOGY}"
        "?valid_at=2027-02-01T00:00:00Z&recorded_at=2027-02-01T00:00:00Z"
    )
    status, body = _http(server, path, authorization=f"Bearer {_token()}")
    assert status == 503
    assert body["error_code"] == "planner_query_failed"
    assert "secret" not in json.dumps(body)


def test_next_action_handles_empty_and_divergent_decisions() -> None:
    """The buyer surface never fabricates one action from conflicting rows."""

    assert service._next_plan_action([]) == "no_impacted_applications"
    assert (
        service._next_plan_action(
            [
                {"recommended_action_code": "approve_target_state"},
                {"recommended_action_code": "schedule_transformation"},
                {"recommended_action_code": None},
            ]
        )
        == "review_target_state_actions"
    )
