"""HTTP acceptance for the purpose-bound portfolio assessment read."""

from __future__ import annotations

import json
from http.client import HTTPConnection
from typing import Any

import pytest

import ea_core_foundation.replan_runtime as replan_runtime
from ea_core_foundation.service import PlannerExecutionError
from tests.test_portfolio_assessment_api import _PATH, _SUMMARY_PATH, _row
from tests.test_target_state_replan_runtime import (
    _config,
    _jwks_loader,
    _patch_main_builders,
    _start_server,
    _stop_server,
    _token,
)

_ROLE = "ea_portfolio_assessment_reader"
_SUMMARY_ROLE = "ea_portfolio_assessment_summary_reader"


def _get(
    host: str,
    port: int,
    *,
    authorization: str | None,
    path: str = _PATH,
) -> tuple[int, dict[str, Any]]:
    """Issue one authenticated JSON GET and return status plus body."""

    connection = HTTPConnection(host, port, timeout=2)
    headers: dict[str, str] = {}
    if authorization is not None:
        headers["Authorization"] = authorization
    try:
        connection.request("GET", path, headers=headers)
        response = connection.getresponse()
        return response.status, json.loads(response.read().decode("utf-8"))
    finally:
        connection.close()


def _portfolio_config():
    """Return the test profile restricted to the portfolio read role."""

    return _config(frozenset({_ROLE}))


def _portfolio_summary_config():
    """Return the test profile restricted to the summary read role."""

    return _config(frozenset({_SUMMARY_ROLE}))


def test_http_portfolio_assessment_is_purpose_authorized_and_actionable() -> None:
    """Only the dedicated role can observe the assessment facts."""

    reads: list[str] = []

    def reader(context: Any, request: Any) -> dict[str, object]:
        reads.append(f"{context.subject_id}:{request.architecture_object_id}")
        return {
            "architecture_object_id": str(request.architecture_object_id),
            "valid_at": "2026-08-20T00:00:00Z",
            "recorded_at": "2026-08-20T01:00:00Z",
            "assessment_count": 1,
            "assessments": [_row()],
        }

    server, thread, host, port = _start_server(
        portfolio_assessment_authorization_config=_portfolio_config(),
        portfolio_assessment_reader=reader,
        jwks_loader=_jwks_loader,
        signature_verifier=lambda signing_input, signature, jwk: True,
    )
    try:
        anonymous_status, anonymous = _get(host, port, authorization=None)
        denied_status, denied = _get(
            host,
            port,
            authorization=f"Bearer {_token('ea_target_state_reader')}",
        )
        ok_status, ok = _get(
            host,
            port,
            authorization=f"Bearer {_token(_ROLE)}",
        )
    finally:
        _stop_server(server, thread)

    assert anonymous_status == 401
    assert anonymous["error_code"] == "authorization_required"
    assert denied_status == 403
    assert denied["error_code"] == "forbidden"
    assert ok_status == 200
    assert ok["assessment_count"] == 1
    assert reads == [
        "target-state-replanner-123:0196f300-1111-7111-8111-111111111174"
    ]


@pytest.mark.parametrize(
    "kwargs",
    [
        {},
        {
            "portfolio_assessment_authorization_config": "not-a-config",
            "portfolio_assessment_reader": "not-a-reader",
        },
    ],
)
def test_http_portfolio_assessment_fails_closed_without_policy_and_reader(
    kwargs: dict[str, object],
) -> None:
    """Reject reads unless both the purpose policy and read port exist."""

    server, thread, host, port = _start_server(**kwargs)
    try:
        status, body = _get(
            host,
            port,
            authorization=f"Bearer {_token(_ROLE)}",
        )
    finally:
        _stop_server(server, thread)

    assert status == 503
    assert body["error_code"] == "portfolio_assessment_unavailable"


def test_http_portfolio_assessment_summary_is_purpose_authorized() -> None:
    """The summary projection has its own role and returns buyer next actions."""

    def reader(context: Any, request: Any) -> dict[str, object]:
        del context, request
        return {
            "architecture_object_id": "0196f300-1111-7111-8111-111111111174",
            "valid_at": "2026-08-20T00:00:00Z",
            "recorded_at": "2026-08-20T01:00:00Z",
            "assessment_count": 0,
            "group_count": 0,
            "assessment_state_code": "no_assessments",
            "next_action": "collect_portfolio_assessments",
            "groups": [],
        }

    server, thread, host, port = _start_server(
        portfolio_assessment_summary_authorization_config=_portfolio_summary_config(),
        portfolio_assessment_summary_reader=reader,
        jwks_loader=_jwks_loader,
        signature_verifier=lambda signing_input, signature, jwk: True,
    )
    try:
        denied_status, denied = _get(
            host,
            port,
            authorization=f"Bearer {_token(_ROLE)}",
            path=_SUMMARY_PATH,
        )
        ok_status, ok = _get(
            host,
            port,
            authorization=f"Bearer {_token(_SUMMARY_ROLE)}",
            path=_SUMMARY_PATH,
        )
    finally:
        _stop_server(server, thread)

    assert denied_status == 403
    assert denied["error_code"] == "forbidden"
    assert ok_status == 200
    assert ok["next_action"] == "collect_portfolio_assessments"


@pytest.mark.parametrize(
    "kwargs",
    [
        {},
        {
            "portfolio_assessment_summary_authorization_config": "not-a-config",
            "portfolio_assessment_summary_reader": "not-a-reader",
        },
    ],
)
def test_http_portfolio_assessment_summary_fails_closed_without_policy_and_reader(
    kwargs: dict[str, object],
) -> None:
    """Reject summary reads unless both the dedicated policy and read port exist."""

    server, thread, host, port = _start_server(**kwargs)
    try:
        status, body = _get(
            host,
            port,
            authorization=f"Bearer {_token(_SUMMARY_ROLE)}",
            path=_SUMMARY_PATH,
        )
    finally:
        _stop_server(server, thread)

    assert status == 503
    assert body["error_code"] == "portfolio_assessment_summary_unavailable"


def test_http_portfolio_assessment_summary_rejects_invalid_target_before_read() -> None:
    """Summary requests preserve the raw read port's local-origin boundary."""

    reads: list[str] = []

    def reader(context: Any, request: Any) -> dict[str, object]:
        del context, request
        reads.append("read")
        return {}

    server, thread, host, port = _start_server(
        portfolio_assessment_summary_authorization_config=_portfolio_summary_config(),
        portfolio_assessment_summary_reader=reader,
        jwks_loader=_jwks_loader,
        signature_verifier=lambda signing_input, signature, jwk: True,
    )
    try:
        status, body = _get(
            host,
            port,
            authorization=f"Bearer {_token(_SUMMARY_ROLE)}",
            path=f"https://attacker.example{_SUMMARY_PATH}",
        )
    finally:
        _stop_server(server, thread)

    assert status == 400
    assert body["error_code"] == "invalid_portfolio_assessment_summary_request"
    assert reads == []


def test_http_portfolio_assessment_summary_reader_failure_is_retriable() -> None:
    """Summary storage failure remains an explicit retriable 503."""

    def failing_reader(context: Any, request: Any) -> dict[str, object]:
        del context, request
        raise PlannerExecutionError("database unavailable")

    server, thread, host, port = _start_server(
        portfolio_assessment_summary_authorization_config=_portfolio_summary_config(),
        portfolio_assessment_summary_reader=failing_reader,
        jwks_loader=_jwks_loader,
        signature_verifier=lambda signing_input, signature, jwk: True,
    )
    try:
        status, body = _get(
            host,
            port,
            authorization=f"Bearer {_token(_SUMMARY_ROLE)}",
            path=_SUMMARY_PATH,
        )
    finally:
        _stop_server(server, thread)

    assert status == 503
    assert body["error_code"] == "portfolio_assessment_summary_read_failed"
    assert "retry" in body["next_action"].lower()


def test_http_portfolio_assessment_rejects_invalid_target_before_read() -> None:
    """Authority-bearing and malformed targets cannot alias a portfolio resource."""

    reads: list[str] = []

    def reader(context: Any, request: Any) -> dict[str, object]:
        del context, request
        reads.append("read")
        return {}

    server, thread, host, port = _start_server(
        portfolio_assessment_authorization_config=_portfolio_config(),
        portfolio_assessment_reader=reader,
        jwks_loader=_jwks_loader,
        signature_verifier=lambda signing_input, signature, jwk: True,
    )
    try:
        status, body = _get(
            host,
            port,
            authorization=f"Bearer {_token(_ROLE)}",
            path=f"https://attacker.example{_PATH}",
        )
    finally:
        _stop_server(server, thread)

    assert status == 400
    assert body["error_code"] == "invalid_portfolio_assessment_request"
    assert reads == []


def test_http_portfolio_assessment_reader_failure_is_retriable() -> None:
    """Storage failure remains an explicit 503 instead of a false assessment."""

    def failing_reader(context: Any, request: Any) -> dict[str, object]:
        del context, request
        raise PlannerExecutionError("database unavailable")

    server, thread, host, port = _start_server(
        portfolio_assessment_authorization_config=_portfolio_config(),
        portfolio_assessment_reader=failing_reader,
        jwks_loader=_jwks_loader,
        signature_verifier=lambda signing_input, signature, jwk: True,
    )
    try:
        status, body = _get(
            host,
            port,
            authorization=f"Bearer {_token(_ROLE)}",
        )
    finally:
        _stop_server(server, thread)

    assert status == 503
    assert body["error_code"] == "portfolio_assessment_read_failed"
    assert "retry" in body["next_action"].lower()


def test_main_wires_portfolio_assessment_policy_and_reader(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Production startup composes the portfolio read into the complete runtime."""

    server = _patch_main_builders(monkeypatch)
    monkeypatch.setattr(
        replan_runtime,
        "build_portfolio_assessment_authorization_config",
        lambda value: "build_portfolio_assessment_authorization_config",
    )
    monkeypatch.setattr(
        replan_runtime,
        "build_portfolio_assessment_reader",
        lambda value: "build_portfolio_assessment_reader",
    )
    monkeypatch.setattr(
        replan_runtime,
        "build_portfolio_assessment_summary_authorization_config",
        lambda value: "build_portfolio_assessment_summary_authorization_config",
    )
    monkeypatch.setattr(
        replan_runtime,
        "build_portfolio_assessment_summary_reader",
        lambda value: "build_portfolio_assessment_summary_reader",
    )
    monkeypatch.setattr(replan_runtime, "serve_forever", lambda current: None)

    assert replan_runtime.main([]) == 0
    assert server.captured["portfolio_assessment_authorization_config"] == (
        "build_portfolio_assessment_authorization_config"
    )
    assert server.captured["portfolio_assessment_reader"] == (
        "build_portfolio_assessment_reader"
    )
    assert server.captured["portfolio_assessment_summary_authorization_config"] == (
        "build_portfolio_assessment_summary_authorization_config"
    )
    assert server.captured["portfolio_assessment_summary_reader"] == (
        "build_portfolio_assessment_summary_reader"
    )
