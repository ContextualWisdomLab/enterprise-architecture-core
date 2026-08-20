"""HTTP acceptance for the purpose-bound data-management reassessment status read."""

from __future__ import annotations

import json
from http.client import HTTPConnection
from typing import Any

import pytest

import ea_core_foundation.replan_runtime as replan_runtime
from ea_core_foundation.service import PlannerExecutionError
from tests.test_data_management_recheck_status_api import _PATH, _payload
from tests.test_target_state_replan_runtime import (
    _config,
    _jwks_loader,
    _patch_main_builders,
    _start_server,
    _stop_server,
    _token,
)

_ROLE = "ea_data_management_recheck_reader"


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


def test_http_recheck_status_is_purpose_authorized_and_actionable() -> None:
    """Only the dedicated read role can observe the reassessment buyer action."""

    reads: list[str] = []

    def reader(context: Any, request: Any) -> dict[str, object]:
        reads.append(f"{context.subject_id}:{request.assessment_recheck_request_id}")
        return _payload()

    server, thread, host, port = _start_server(
        data_management_recheck_status_authorization_config=_config(frozenset({_ROLE})),
        data_management_recheck_status_reader=reader,
        jwks_loader=_jwks_loader,
        signature_verifier=lambda signing_input, signature, jwk: True,
    )
    try:
        anonymous_status, anonymous = _get(host, port, authorization=None)
        denied_status, denied = _get(
            host,
            port,
            authorization=f"Bearer {_token('ea_data_management_rechecker')}",
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
    assert ok["next_action"] == "plan_remaining_assessment_gap"
    assert reads == [
        "target-state-replanner-123:0196f300-1111-7111-8111-111111111174"
    ]


@pytest.mark.parametrize(
    "kwargs",
    [
        {},
        {
            "data_management_recheck_status_authorization_config": "not-a-config",
            "data_management_recheck_status_reader": "not-a-reader",
        },
    ],
)
def test_http_recheck_status_fails_closed_without_policy_and_reader(
    kwargs: dict[str, object],
) -> None:
    """Reject status reads unless both least-privilege policy and read port exist."""

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
    assert body["error_code"] == "data_management_recheck_status_unavailable"


def test_http_recheck_status_rejects_invalid_target_before_read() -> None:
    """Authority-bearing or nested targets cannot alias a local reassessment resource."""

    reads: list[str] = []

    def reader(context: Any, request: Any) -> dict[str, object]:
        del context, request
        reads.append("read")
        return _payload()

    server, thread, host, port = _start_server(
        data_management_recheck_status_authorization_config=_config(frozenset({_ROLE})),
        data_management_recheck_status_reader=reader,
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
    assert body["error_code"] == "invalid_data_management_recheck_status_request"
    assert reads == []


def test_http_recheck_status_reader_failure_never_looks_complete() -> None:
    """Storage failures remain an explicit retriable 503 rather than fake success."""

    def reader(context: Any, request: Any) -> dict[str, object]:
        del context, request
        raise PlannerExecutionError("database unavailable")

    server, thread, host, port = _start_server(
        data_management_recheck_status_authorization_config=_config(frozenset({_ROLE})),
        data_management_recheck_status_reader=reader,
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
    assert body["error_code"] == "data_management_recheck_status_read_failed"
    assert "retry" in body["next_action"].lower()


def test_main_wires_recheck_status_policy_and_reader(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Production startup composes the reassessment status read into one runtime."""

    server = _patch_main_builders(monkeypatch)
    monkeypatch.setattr(
        replan_runtime,
        "build_data_management_recheck_status_authorization_config",
        lambda value: "build_data_management_recheck_status_authorization_config",
    )
    monkeypatch.setattr(
        replan_runtime,
        "build_data_management_recheck_status_reader",
        lambda value: "build_data_management_recheck_status_reader",
    )
    monkeypatch.setattr(replan_runtime, "serve_forever", lambda current: None)

    assert replan_runtime.main([]) == 0
    assert server.captured[
        "data_management_recheck_status_authorization_config"
    ] == "build_data_management_recheck_status_authorization_config"
    assert server.captured["data_management_recheck_status_reader"] == (
        "build_data_management_recheck_status_reader"
    )
