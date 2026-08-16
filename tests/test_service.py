"""Executable tests for the implemented health and ready process surface."""

from __future__ import annotations

import json
import threading
from http.client import HTTPConnection
from typing import Any

import pytest

from ea_core_foundation import (
    BindAddress,
    build_health_report,
    build_readiness_report,
    classify_request,
    create_service_server,
    resolve_bind_address,
    serve_foundation,
)
from ea_core_foundation.service import (
    FoundationServiceHandler,
    main,
    serve_forever,
)


def test_health_report_names_the_product_not_a_legacy_alias() -> None:
    """Operators should see the current product name in the liveness payload."""

    report = build_health_report()
    assert report.as_mapping() == {
        "service_name": "enterprise-architecture-core",
        "status_code": "alive",
    }


@pytest.mark.parametrize(
    ("contract_ready", "database_ready", "status_code", "http_status"),
    [
        (True, True, "ready", 200),
        (True, False, "not_ready", 503),
        (False, True, "not_ready", 503),
        (False, False, "not_ready", 503),
    ],
)
def test_readiness_report_uses_both_dependency_checks(
    contract_ready: bool,
    database_ready: bool,
    status_code: str,
    http_status: int,
) -> None:
    """Traffic should wait until contracts and the database are both ready."""

    report = build_readiness_report(
        contract_ready=contract_ready,
        database_probe=lambda: database_ready,
    )
    assert report.status_code == status_code
    assert report.http_status() == http_status
    assert report.as_mapping()["database_ready"] is database_ready


def test_readiness_without_a_probe_stays_out_of_the_serving_pool() -> None:
    """A missing database probe is not treated as a passing dependency."""

    report = build_readiness_report(contract_ready=True)
    assert report.status_code == "not_ready"
    assert report.database_ready is False


def test_bind_address_defaults_to_all_interfaces_and_port_env() -> None:
    """Render-style hosts bind 0.0.0.0 and honor the PORT environment variable."""

    assert resolve_bind_address(environ={}) == BindAddress("0.0.0.0", 8080)
    assert resolve_bind_address(environ={"PORT": "9090"}) == BindAddress(
        "0.0.0.0", 9090
    )
    assert resolve_bind_address(
        host="127.0.0.1",
        port=18080,
        environ={"EA_BIND_HOST": "ignored", "PORT": "1"},
    ) == BindAddress("127.0.0.1", 18080)
    assert resolve_bind_address(environ={"EA_BIND_HOST": "127.0.0.1"}) == BindAddress(
        "127.0.0.1", 8080
    )


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"port": "abc"}, "PORT must be an integer"),
        ({"port": 0}, "PORT must be between 1 and 65535"),
        ({"port": 65536}, "PORT must be between 1 and 65535"),
        ({"host": ""}, "bind host must be non-empty"),
    ],
)
def test_bind_address_rejects_unusable_listen_values(
    kwargs: dict[str, Any], message: str
) -> None:
    """A process that cannot listen should fail before claiming readiness."""

    with pytest.raises(ValueError, match=message):
        resolve_bind_address(environ={}, **kwargs)


def test_classify_request_accepts_query_strings_on_documented_paths() -> None:
    """Probes may append query parameters without changing the route."""

    assert classify_request("get", "/health?source=load-balancer") == (
        "GET",
        "health",
    )
    assert classify_request("GET", "/ready") == ("GET", "ready")
    assert classify_request("POST", "/missing") == ("OTHER", "not_found")


def _request(
    host: str, port: int, method: str, path: str
) -> tuple[int, dict[str, Any]]:
    """Issue one HTTP request against the in-process foundation server."""

    connection = HTTPConnection(host, port, timeout=2)
    try:
        connection.request(method, path)
        response = connection.getresponse()
        payload = json.loads(response.read().decode("utf-8"))
        return response.status, payload
    finally:
        connection.close()


def test_http_surface_serves_health_ready_and_operator_errors() -> None:
    """The advertised OpenAPI paths are implemented and unknown writes fail closed."""

    server = create_service_server(
        BindAddress("127.0.0.1", 0),
        contract_ready=True,
        database_probe=lambda: True,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address[:2]
    try:
        health_status, health_body = _request(host, port, "GET", "/health")
        ready_status, ready_body = _request(host, port, "GET", "/ready")
        missing_status, missing_body = _request(host, port, "GET", "/commands")
        write_status, write_body = _request(host, port, "POST", "/health")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert health_status == 200
    assert health_body["status_code"] == "alive"
    assert ready_status == 200
    assert ready_body["status_code"] == "ready"
    assert missing_status == 404
    assert missing_body["next_action"].startswith("Call GET /health")
    assert write_status == 405
    assert "GET /health" in write_body["next_action"]


def test_http_ready_without_a_configured_probe_is_not_ready() -> None:
    """The default process stays out of the pool until a database probe exists."""

    server = create_service_server(BindAddress("127.0.0.1", 0))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address[:2]
    try:
        status, body = _request(host, port, "GET", "/ready")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert status == 503
    assert body["contract_ready"] is True
    assert body["database_ready"] is False


def test_http_ready_treats_a_non_callable_probe_as_missing() -> None:
    """A misconfigured probe must not be invoked as a bound handler method."""

    server = create_service_server(
        BindAddress("127.0.0.1", 0),
        contract_ready=True,
        database_probe="not-a-probe",  # type: ignore[arg-type]
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address[:2]
    try:
        status, body = _request(host, port, "GET", "/ready")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert status == 503
    assert body["database_ready"] is False


def test_http_ready_stays_503_when_a_dependency_fails() -> None:
    """A failed database probe keeps the instance out of the serving pool."""

    server = create_service_server(
        BindAddress("127.0.0.1", 0),
        contract_ready=False,
        database_probe=lambda: False,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address[:2]
    try:
        status, body = _request(host, port, "GET", "/ready")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert status == 503
    assert body["status_code"] == "not_ready"
    assert body["contract_ready"] is False
    assert body["database_ready"] is False


def test_main_returns_cleanly_on_supervisor_interrupt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """SIGINT from a process supervisor is a successful shutdown."""

    created: list[Any] = []

    class FakeServer:
        """Record close() so the shutdown path is observable."""

        def server_close(self) -> None:
            """Mark the listen socket as released."""

            created.append("closed")

    monkeypatch.setattr(
        "ea_core_foundation.service.resolve_bind_address",
        lambda: BindAddress("127.0.0.1", 18080),
    )
    monkeypatch.setattr(
        "ea_core_foundation.service.create_service_server",
        lambda bind_address, **kwargs: created.append(bind_address) or FakeServer(),
    )
    monkeypatch.setattr(
        "ea_core_foundation.service.serve_forever",
        lambda server: (_ for _ in ()).throw(KeyboardInterrupt()),
    )

    assert main([]) == 0
    assert created[0] == BindAddress("127.0.0.1", 18080)
    assert created[-1] == "closed"
    assert serve_foundation is main


def test_main_returns_zero_after_a_clean_serve(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A supervisor that stops the server without SIGINT is still a clean exit."""

    class FakeServer:
        """Record close() after a non-interrupt serve loop."""

        def server_close(self) -> None:
            """Mark the listen socket as released."""

            return None

    monkeypatch.setattr(
        "ea_core_foundation.service.resolve_bind_address",
        lambda: BindAddress("127.0.0.1", 18081),
    )
    monkeypatch.setattr(
        "ea_core_foundation.service.create_service_server",
        lambda bind_address, **kwargs: FakeServer(),
    )
    monkeypatch.setattr("ea_core_foundation.service.serve_forever", lambda server: None)
    assert main() == 0


def test_serve_forever_delegates_to_the_http_server() -> None:
    """The blocking helper is the process-supervisor integration point."""

    calls: list[str] = []

    class FakeServer:
        """Capture serve_forever so the helper can be tested without a socket."""

        def serve_forever(self) -> None:
            """Record that the supervisor asked the server to block."""

            calls.append("served")

    serve_forever(FakeServer())  # type: ignore[arg-type]
    assert calls == ["served"]


def test_handler_log_message_keeps_the_stdlib_operator_log(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Access logs remain available without becoming a second product surface."""

    handler = FoundationServiceHandler.__new__(FoundationServiceHandler)
    handler.address_string = lambda: "127.0.0.1"  # type: ignore[method-assign]
    handler.log_message("GET %s %s", "/health", "200")
    captured = capsys.readouterr()
    assert "/health" in captured.err
