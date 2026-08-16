"""Process liveness and readiness HTTP surface for Enterprise Architecture Core."""

from __future__ import annotations

import json
import os
import subprocess
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.metadata import PackageNotFoundError, version as distribution_version
from typing import Literal
from urllib.parse import unquote, urlparse

SERVICE_NAME = "enterprise-architecture-core"
DEFAULT_BIND_HOST = "0.0.0.0"
DEFAULT_BIND_PORT = 8080
CONTEXT_CONTRACT_DISTRIBUTION = "cwl-context-contracts"
SUPPORTED_CONTEXT_CONTRACT_VERSION = "0.1.0"
_DATABASE_DSN_ENV = "EA_DATABASE_DSN"
_DATABASE_READINESS_SQL = """
SELECT (
    current_database() = 'ea_core'
    AND current_user = 'ea_runtime'
    AND to_regnamespace('architecture_core') IS NOT NULL
    AND to_regclass('architecture_core.architecture_object_reference') IS NOT NULL
    AND to_regclass('architecture_core.application_record') IS NOT NULL
    AND NOT has_table_privilege(
        current_user,
        'architecture_core.application_record',
        'SELECT'
    )
);
""".strip()

ReadinessProbe = Callable[[], bool]
VersionReader = Callable[[str], str]
CommandRunner = Callable[..., subprocess.CompletedProcess[str]]
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


def probe_context_contract(
    *,
    version_reader: VersionReader = distribution_version,
) -> bool:
    """Return whether the exact supported Context Graph contract is installed."""

    try:
        installed_version = version_reader(CONTEXT_CONTRACT_DISTRIBUTION)
    except PackageNotFoundError:
        return False
    return installed_version == SUPPORTED_CONTEXT_CONTRACT_VERSION


def _false_probe() -> bool:
    """Return a reusable fail-closed dependency probe."""

    return False


def _postgres_environment(
    dsn: str,
    base_environment: Mapping[str, str] | None,
) -> dict[str, str] | None:
    """Translate the documented PostgreSQL URI into libpq environment values."""

    try:
        parsed = urlparse(dsn)
        port = parsed.port or 5432
    except ValueError:
        return None
    database_name = unquote(parsed.path.lstrip("/"))
    required_parts = (
        parsed.scheme in {"postgres", "postgresql"},
        parsed.hostname is not None,
        parsed.username is not None,
        parsed.password is not None,
        bool(database_name),
    )
    if not all(required_parts):
        return None
    environment = dict(os.environ if base_environment is None else base_environment)
    environment.update(
        {
            "PGHOST": parsed.hostname or "",
            "PGPORT": str(port),
            "PGUSER": unquote(parsed.username or ""),
            "PGPASSWORD": unquote(parsed.password or ""),
            "PGDATABASE": database_name,
            "PGCONNECT_TIMEOUT": "3",
        }
    )
    return environment


def build_database_readiness_probe(
    dsn: str | None,
    *,
    runner: CommandRunner = subprocess.run,
    base_environment: Mapping[str, str] | None = None,
) -> ReadinessProbe:
    """Build a fail-closed PostgreSQL probe without granting table authority."""

    if not dsn:
        return _false_probe
    connection_environment = _postgres_environment(dsn, base_environment)
    if connection_environment is None:
        return _false_probe

    def probe() -> bool:
        """Authenticate as the runtime role and prove the expected schema boundary."""

        try:
            result = runner(
                [
                    "psql",
                    "--no-psqlrc",
                    "--tuples-only",
                    "--no-align",
                    "--set",
                    "ON_ERROR_STOP=1",
                    "--command",
                    _DATABASE_READINESS_SQL,
                ],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
                env=connection_environment,
            )
        except (OSError, subprocess.TimeoutExpired):
            return False
        return result.returncode == 0 and result.stdout.strip() == "t"

    return probe


def build_health_report() -> HealthReport:
    """Return process liveness. Call GET /ready before sending tenant traffic."""

    return HealthReport(service_name=SERVICE_NAME, status_code="alive")


def _run_readiness_probe(probe: ReadinessProbe | None) -> bool:
    """Execute one dependency probe and fail closed on probe exceptions."""

    if probe is None:
        return False
    try:
        return bool(probe())
    except Exception:
        return False


def build_readiness_report(
    *,
    contract_ready: bool,
    database_probe: ReadinessProbe | None = None,
) -> ReadinessReport:
    """Return readiness from an exact contract check and database probe."""

    database_ready = _run_readiness_probe(database_probe)
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
        """Read the contract probe result from the bound server, failing closed."""

        return bool(getattr(self.server, "contract_ready", False))

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
    contract_ready: bool = False,
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
    """Start the fail-closed runtime surface on ``0.0.0.0:$PORT``."""

    del argv
    environment: Mapping[str, str] = os.environ
    bind_address = resolve_bind_address(environ=environment)
    database_probe = build_database_readiness_probe(
        environment.get(_DATABASE_DSN_ENV)
    )
    server = create_service_server(
        bind_address,
        contract_ready=probe_context_contract(),
        database_probe=database_probe,
    )
    try:
        serve_forever(server)
    except KeyboardInterrupt:
        return 0
    finally:
        server.server_close()
    return 0
