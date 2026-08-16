"""Process liveness and readiness HTTP surface for Enterprise Architecture Core."""

from __future__ import annotations

import json
import os
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Literal
from urllib.parse import urlparse

SERVICE_NAME = "enterprise-architecture-core"
DEFAULT_BIND_HOST = "0.0.0.0"
DEFAULT_BIND_PORT = 8080

ReadinessProbe = Callable[[], bool]
HttpMethod = Literal["GET", "OTHER"]
RouteName = Literal["health", "ready", "not_found"]


@dataclass(frozen=True, slots=True)
class BindAddress:
    """Host and TCP port the process should listen on."""

    bind_host: str
    bind_port: int


@dataclass(frozen=True, slots=True)
class HealthReport:
    """Liveness payload advertised by GET /health."""

    service_name: str
    status_code: Literal["alive"]

    def as_mapping(self) -> dict[str, str]:
        """Return the JSON object a load balancer should parse next."""

        return {
            "service_name": self.service_name,
            "status_code": self.status_code,
        }


@dataclass(frozen=True, slots=True)
class ReadinessReport:
    """Readiness payload advertised by GET /ready."""

    service_name: str
    status_code: Literal["ready", "not_ready"]
    contract_ready: bool
    database_ready: bool

    def as_mapping(self) -> dict[str, object]:
        """Return the JSON object an operator should inspect before traffic."""

        return {
            "service_name": self.service_name,
            "status_code": self.status_code,
            "contract_ready": self.contract_ready,
            "database_ready": self.database_ready,
        }

    def http_status(self) -> int:
        """Return 200 only when every required dependency is ready."""

        return 200 if self.status_code == "ready" else 503


def resolve_bind_address(
    host: str | None = None,
    port: str | int | None = None,
    environ: Mapping[str, str] | None = None,
) -> BindAddress:
    """Resolve the Render-compatible bind address from values or the environment."""

    environment = os.environ if environ is None else environ
    bind_host = DEFAULT_BIND_HOST if host is None else host
    if host is None:
        bind_host = environment.get("EA_BIND_HOST", DEFAULT_BIND_HOST)
    raw_port: str | int
    if port is None:
        raw_port = environment.get("PORT", str(DEFAULT_BIND_PORT))
    else:
        raw_port = port
    try:
        bind_port = int(raw_port)
    except (TypeError, ValueError) as error:
        raise ValueError("PORT must be an integer") from error
    if bind_port < 1 or bind_port > 65535:
        raise ValueError("PORT must be between 1 and 65535")
    if not bind_host:
        raise ValueError("bind host must be non-empty")
    return BindAddress(bind_host=bind_host, bind_port=bind_port)


def build_health_report() -> HealthReport:
    """Return process liveness. Call GET /ready before sending tenant traffic."""

    return HealthReport(service_name=SERVICE_NAME, status_code="alive")


def build_readiness_report(
    *,
    contract_ready: bool,
    database_probe: ReadinessProbe | None = None,
) -> ReadinessReport:
    """Return readiness from contract presence and an optional database probe."""

    database_ready = False if database_probe is None else database_probe()
    status_code: Literal["ready", "not_ready"]
    if contract_ready and database_ready:
        status_code = "ready"
    else:
        status_code = "not_ready"
    return ReadinessReport(
        service_name=SERVICE_NAME,
        status_code=status_code,
        contract_ready=contract_ready,
        database_ready=database_ready,
    )


def classify_request(method: str, path: str) -> tuple[HttpMethod, RouteName]:
    """Classify an HTTP request into a documented route or a rejection."""

    normalized_method: HttpMethod = "GET" if method.upper() == "GET" else "OTHER"
    normalized_path = urlparse(path).path or "/"
    if normalized_path == "/health":
        route: RouteName = "health"
    elif normalized_path == "/ready":
        route = "ready"
    else:
        route = "not_found"
    return normalized_method, route


class FoundationServiceHandler(BaseHTTPRequestHandler):
    """Serve the documented liveness and readiness endpoints."""

    server_version = "EACore/0.1"
    def _contract_ready(self) -> bool:
        """Read the contract probe from the bound server, defaulting to ready."""

        return bool(getattr(self.server, "contract_ready", True))

    def _database_probe(self) -> ReadinessProbe | None:
        """Read the optional database probe from the bound server."""

        probe = getattr(self.server, "database_probe", None)
        if probe is None or callable(probe):
            return probe
        return None

    def do_GET(self) -> None:
        """Handle documented GET routes and reject unknown paths."""

        self._dispatch("GET")

    def do_POST(self) -> None:
        """Reject writes on the foundation runtime surface."""

        self._dispatch("POST")

    def _dispatch(self, method: str) -> None:
        """Route one request to the matching documented response."""

        verb, route = classify_request(method, self.path)
        if verb == "OTHER":
            self._write_json(
                405,
                {
                    "error_code": "method_not_allowed",
                    "next_action": "Use GET /health or GET /ready.",
                },
            )
            return
        if route == "health":
            self._write_json(200, build_health_report().as_mapping())
            return
        if route == "ready":
            report = build_readiness_report(
                contract_ready=self._contract_ready(),
                database_probe=self._database_probe(),
            )
            self._write_json(report.http_status(), report.as_mapping())
            return
        self._write_json(
            404,
            {
                "error_code": "not_found",
                "next_action": "Call GET /health or GET /ready.",
            },
        )

    def _write_json(self, status: int, payload: Mapping[str, object]) -> None:
        """Write a JSON response an operator or probe can act on immediately."""

        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        """Keep operator logs available without leaking request bodies."""

        super().log_message(format, *args)


def create_service_server(
    bind_address: BindAddress,
    *,
    contract_ready: bool = True,
    database_probe: ReadinessProbe | None = None,
) -> ThreadingHTTPServer:
    """Create a bound server. Callers must shut it down after use."""

    server = ThreadingHTTPServer(
        (bind_address.bind_host, bind_address.bind_port),
        FoundationServiceHandler,
    )
    server.contract_ready = contract_ready
    server.database_probe = database_probe
    return server


def serve_forever(server: ThreadingHTTPServer) -> None:
    """Block until the server is shut down by the process supervisor."""

    server.serve_forever()


def main(argv: Sequence[str] | None = None) -> int:
    """Start the foundation HTTP surface on ``0.0.0.0:$PORT``."""

    del argv
    bind_address = resolve_bind_address()
    server = create_service_server(bind_address)
    try:
        serve_forever(server)
    except KeyboardInterrupt:
        return 0
    finally:
        server.server_close()
    return 0
