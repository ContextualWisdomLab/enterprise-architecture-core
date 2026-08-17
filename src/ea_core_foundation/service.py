"""Process health, readiness, and authenticated EA decision HTTP surfaces."""

from __future__ import annotations

import json
import os
import subprocess
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as distribution_version
from typing import Literal
from urllib.parse import parse_qsl, unquote, urlparse
from uuid import UUID

from .authorization import (
    AuthorizationContext,
    AuthorizationError,
    JwksLoader,
    KeyverseAuthorizationConfig,
    SignatureVerifier,
    build_keyverse_authorization_config,
    load_keyverse_jwks,
    verify_keyverse_bearer,
    verify_rs256_signature,
)

SERVICE_NAME = "enterprise-architecture-core"
DEFAULT_BIND_HOST = "0.0.0.0"
DEFAULT_BIND_PORT = 8080
CONTEXT_CONTRACT_DISTRIBUTION = "cwl-context-contracts"
SUPPORTED_CONTEXT_CONTRACT_VERSION = "0.1.0"
_DATABASE_DSN_ENV = "EA_DATABASE_DSN"
_TARGET_STATE_PATH_PREFIX = "/v1/technology-target-state-plans/"
_LIBPQ_QUERY_ENVIRONMENT = {
    "host": "PGHOST",
    "hostaddr": "PGHOSTADDR",
    "port": "PGPORT",
    "dbname": "PGDATABASE",
    "user": "PGUSER",
    "password": "PGPASSWORD",
    "passfile": "PGPASSFILE",
    "require_auth": "PGREQUIREAUTH",
    "channel_binding": "PGCHANNELBINDING",
    "service": "PGSERVICE",
    "options": "PGOPTIONS",
    "application_name": "PGAPPNAME",
    "sslnegotiation": "PGSSLNEGOTIATION",
    "sslmode": "PGSSLMODE",
    "requiressl": "PGREQUIRESSL",
    "sslcompression": "PGSSLCOMPRESSION",
    "sslcert": "PGSSLCERT",
    "sslkey": "PGSSLKEY",
    "sslcertmode": "PGSSLCERTMODE",
    "sslrootcert": "PGSSLROOTCERT",
    "sslcrl": "PGSSLCRL",
    "sslcrldir": "PGSSLCRLDIR",
    "sslsni": "PGSSLSNI",
    "requirepeer": "PGREQUIREPEER",
    "ssl_min_protocol_version": "PGSSLMINPROTOCOLVERSION",
    "ssl_max_protocol_version": "PGSSLMAXPROTOCOLVERSION",
    "gssencmode": "PGGSSENCMODE",
    "krbsrvname": "PGKRBSRVNAME",
    "gsslib": "PGGSSLIB",
    "gssdelegation": "PGGSSDELEGATION",
    "connect_timeout": "PGCONNECT_TIMEOUT",
    "client_encoding": "PGCLIENTENCODING",
    "target_session_attrs": "PGTARGETSESSIONATTRS",
    "load_balance_hosts": "PGLOADBALANCEHOSTS",
    "min_protocol_version": "PGMINPROTOCOLVERSION",
    "max_protocol_version": "PGMAXPROTOCOLVERSION",
}
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
_TARGET_STATE_PLAN_SQL = """
SELECT COALESCE(
    json_agg(
        row_to_json(plan)
        ORDER BY
            plan.application_object_id,
            plan.capability_object_id NULLS FIRST,
            plan.external_object_kind_code NULLS FIRST,
            plan.external_context_reference_id NULLS FIRST
    ),
    '[]'::json
)::text
FROM architecture_core.read_technology_target_state_plan(
    :'tenant_record_id'::uuid,
    :'technology_version_id'::uuid,
    :'valid_at'::timestamptz,
    :'recorded_at'::timestamptz,
    :'planning_horizon_days'::integer
) AS plan;
""".strip()

ReadinessProbe = Callable[[], bool]
VersionReader = Callable[[str], str]
CommandRunner = Callable[..., subprocess.CompletedProcess[str]]
HttpMethod = Literal["GET", "OTHER"]
RouteName = Literal["health", "ready", "target_state_plan", "not_found"]


class PlannerRequestError(ValueError):
    """Raised when a planner URL cannot be bound to an exact read request."""


class PlannerExecutionError(RuntimeError):
    """Raised when the purpose-bound database query cannot return safe evidence."""


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


@dataclass(frozen=True, slots=True)
class TargetStatePlanRequest:
    """One exact bitemporal technology planning query."""

    technology_version_id: UUID
    valid_at: datetime
    recorded_at: datetime
    planning_horizon_days: int

    @classmethod
    def from_values(
        cls,
        technology_version_id: str,
        valid_at: str,
        recorded_at: str,
        planning_horizon_days: int = 180,
    ) -> TargetStatePlanRequest:
        """Validate and normalize one buyer query from HTTP-safe strings."""

        try:
            technology_id = UUID(technology_version_id)
        except ValueError as error:
            raise PlannerRequestError(
                "technology version id must be a UUID"
            ) from error
        valid_time = _parse_timestamp(valid_at, "valid_at")
        recorded_time = _parse_timestamp(recorded_at, "recorded_at")
        if planning_horizon_days < 1 or planning_horizon_days > 3650:
            raise PlannerRequestError(
                "planning_horizon_days must be between 1 and 3650"
            )
        return cls(
            technology_version_id=technology_id,
            valid_at=valid_time,
            recorded_at=recorded_time,
            planning_horizon_days=planning_horizon_days,
        )


TargetStatePlanReader = Callable[
    [AuthorizationContext, TargetStatePlanRequest],
    Sequence[Mapping[str, object]],
]


def _parse_timestamp(value: str, field_name: str) -> datetime:
    """Parse an offset-aware RFC 3339-style timestamp and normalize to UTC."""

    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise PlannerRequestError(
            f"{field_name} must be an RFC 3339 timestamp"
        ) from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise PlannerRequestError(f"{field_name} must include a UTC offset")
    return parsed.astimezone(UTC)


def parse_target_state_request(path: str) -> TargetStatePlanRequest:
    """Parse one exact planner path without accepting duplicate/unknown parameters."""

    parsed = urlparse(path)
    if not parsed.path.startswith(_TARGET_STATE_PATH_PREFIX):
        raise PlannerRequestError("target-state planner path is invalid")
    technology_version_id = parsed.path.removeprefix(_TARGET_STATE_PATH_PREFIX)
    if not technology_version_id or "/" in technology_version_id:
        raise PlannerRequestError("target-state planner requires one technology UUID")
    pairs = parse_qsl(parsed.query, keep_blank_values=True)
    allowed_names = {"valid_at", "recorded_at", "planning_horizon_days"}
    if any(name not in allowed_names for name, _ in pairs):
        raise PlannerRequestError(
            "target-state planner query contains unknown parameters"
        )
    values: dict[str, str] = {}
    for name, value in pairs:
        if name in values:
            raise PlannerRequestError(
                f"duplicate planner query parameter: {name}"
            )
        values[name] = value
    if not values.get("valid_at") or not values.get("recorded_at"):
        raise PlannerRequestError("valid_at and recorded_at are required")
    raw_horizon = values.get("planning_horizon_days", "180")
    try:
        horizon = int(raw_horizon)
    except ValueError as error:
        raise PlannerRequestError(
            "planning_horizon_days must be an integer"
        ) from error
    return TargetStatePlanRequest.from_values(
        technology_version_id,
        values["valid_at"],
        values["recorded_at"],
        horizon,
    )


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
    except Exception:
        return False
    return installed_version == SUPPORTED_CONTEXT_CONTRACT_VERSION


def _false_probe() -> bool:
    """Return a reusable fail-closed dependency probe."""

    return False


def _postgres_authority_host_port(
    netloc: str,
) -> tuple[str | None, str | None] | None:
    """Preserve PostgreSQL URI host order, ports, IPv6, and socket directories."""

    host_specification = netloc.rpartition("@")[2]
    if not host_specification:
        return None, None

    host_values: list[str] = []
    port_values: list[str] = []
    has_explicit_port = False
    try:
        for host_entry in host_specification.split(","):
            parsed_entry = urlparse(f"postgresql://{host_entry}")
            host_values.append(unquote(parsed_entry.hostname or ""))
            entry_port = parsed_entry.port
            port_values.append("" if entry_port is None else str(entry_port))
            has_explicit_port = has_explicit_port or entry_port is not None
    except ValueError:
        return None

    host_list = ",".join(host_values)
    port_list = ",".join(port_values) if has_explicit_port else None
    return host_list, port_list


def _postgres_environment(
    dsn: str,
    base_environment: Mapping[str, str] | None,
) -> dict[str, str] | None:
    """Translate one PostgreSQL URI to equivalent supported libpq environment values."""

    try:
        parsed = urlparse(dsn)
        query_items = parse_qsl(parsed.query, keep_blank_values=True)
    except ValueError:
        return None
    if parsed.scheme not in {"postgres", "postgresql"}:
        return None

    authority_host_port = _postgres_authority_host_port(parsed.netloc)
    if authority_host_port is None:
        return None
    authority_host, authority_port = authority_host_port

    query_parameters: dict[str, str] = {}
    for name, value in query_items:
        environment_name = _LIBPQ_QUERY_ENVIRONMENT.get(name)
        if environment_name is None or name in query_parameters:
            return None
        query_parameters[name] = value

    environment = dict(os.environ if base_environment is None else base_environment)
    if authority_host is not None:
        environment["PGHOST"] = authority_host
    if authority_port is not None:
        environment["PGPORT"] = authority_port
    if parsed.username is not None:
        environment["PGUSER"] = unquote(parsed.username)
    if parsed.password is not None:
        environment["PGPASSWORD"] = unquote(parsed.password)
    database_name = unquote(parsed.path.lstrip("/"))
    if database_name:
        environment["PGDATABASE"] = database_name

    for name, value in query_parameters.items():
        environment[_LIBPQ_QUERY_ENVIRONMENT[name]] = value

    environment.setdefault("PGCONNECT_TIMEOUT", "3")
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


def _unavailable_plan_reader(
    context: AuthorizationContext,
    request: TargetStatePlanRequest,
) -> Sequence[Mapping[str, object]]:
    """Reject planner reads when a safe PostgreSQL runtime connection is absent."""

    del context, request
    raise PlannerExecutionError("target-state planner database is unavailable")


def build_target_state_plan_reader(
    dsn: str | None,
    *,
    runner: CommandRunner = subprocess.run,
    base_environment: Mapping[str, str] | None = None,
) -> TargetStatePlanReader:
    """Build the purpose-bound runtime reader without exposing DSN credentials."""

    if not dsn:
        return _unavailable_plan_reader
    connection_environment = _postgres_environment(dsn, base_environment)
    if connection_environment is None:
        return _unavailable_plan_reader

    def reader(
        context: AuthorizationContext,
        request: TargetStatePlanRequest,
    ) -> Sequence[Mapping[str, object]]:
        """Execute one tenant-bound read through the sole granted database function."""

        command = [
            "psql",
            "--no-psqlrc",
            "--tuples-only",
            "--no-align",
            "--set",
            "ON_ERROR_STOP=1",
            "--set",
            f"tenant_record_id={context.tenant_record_id}",
            "--set",
            f"technology_version_id={request.technology_version_id}",
            "--set",
            f"valid_at={request.valid_at.isoformat()}",
            "--set",
            f"recorded_at={request.recorded_at.isoformat()}",
            "--set",
            f"planning_horizon_days={request.planning_horizon_days}",
            "--command",
            _TARGET_STATE_PLAN_SQL,
        ]
        try:
            result = runner(
                command,
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
                env=connection_environment,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            raise PlannerExecutionError(
                "target-state planner database command failed"
            ) from error
        if result.returncode != 0:
            raise PlannerExecutionError("target-state planner database query failed")
        try:
            payload = json.loads(result.stdout.strip())
        except json.JSONDecodeError as error:
            raise PlannerExecutionError(
                "target-state planner returned invalid JSON"
            ) from error
        if not isinstance(payload, list) or any(
            not isinstance(decision, Mapping) for decision in payload
        ):
            raise PlannerExecutionError(
                "target-state planner returned an invalid decision collection"
            )
        return payload

    return reader


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
    elif normalized_path.startswith(_TARGET_STATE_PATH_PREFIX):
        route = "target_state_plan"
    else:
        route = "not_found"
    return normalized_method, route


def _next_plan_action(decisions: Sequence[Mapping[str, object]]) -> str:
    """Return the single shared buyer action or an explicit review instruction."""

    if not decisions:
        return "no_impacted_applications"
    actions = {
        value
        for decision in decisions
        if isinstance((value := decision.get("recommended_action_code")), str)
        and value
    }
    if len(actions) == 1:
        return next(iter(actions))
    return "review_target_state_actions"


class FoundationServiceHandler(BaseHTTPRequestHandler):
    """Serve health, readiness, and authenticated EA decision reads."""

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

    def _authorization_config(self) -> KeyverseAuthorizationConfig | None:
        """Return the configured Keyverse RP profile or fail closed."""

        config = getattr(self.server, "authorization_config", None)
        return config if isinstance(config, KeyverseAuthorizationConfig) else None

    def _plan_reader(self) -> TargetStatePlanReader | None:
        """Return the configured purpose-bound planner reader."""

        reader = getattr(self.server, "target_state_plan_reader", None)
        return reader if callable(reader) else None

    def do_GET(self) -> None:
        """Handle documented GET routes and reject unknown paths."""

        self._dispatch("GET")

    def do_POST(self) -> None:
        """Reject writes on the current runtime surface."""

        self._dispatch("POST")

    def _dispatch(self, method: str) -> None:
        """Route one request to the matching documented response or rejection."""

        verb, route = classify_request(method, self.path)
        if verb == "OTHER":
            self._write_json(
                405,
                {
                    "error_code": "method_not_allowed",
                    "next_action": "Use a documented GET endpoint such as /health.",
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
        if route == "target_state_plan":
            self._serve_target_state_plan()
            return
        self._write_json(
            404,
            {
                "error_code": "not_found",
                "next_action": "Call GET /health or GET /ready.",
            },
        )

    def _serve_target_state_plan(self) -> None:
        """Authorize, validate, execute, and return one buyer planning read."""

        config = self._authorization_config()
        reader = self._plan_reader()
        if config is None or reader is None:
            self._write_json(
                503,
                {
                    "error_code": "planner_unavailable",
                    "next_action": (
                        "Configure Keyverse authorization and the EA runtime database."
                    ),
                },
            )
            return
        jwks_loader = getattr(self.server, "jwks_loader", load_keyverse_jwks)
        signature_verifier = getattr(
            self.server,
            "signature_verifier",
            verify_rs256_signature,
        )
        try:
            context = verify_keyverse_bearer(
                self.headers.get("Authorization"),
                config,
                jwks_loader=jwks_loader,
                signature_verifier=signature_verifier,
            )
        except AuthorizationError as error:
            self._write_json(
                error.http_status,
                {
                    "error_code": error.error_code,
                    "next_action": error.next_action,
                },
            )
            return
        try:
            request = parse_target_state_request(self.path)
        except PlannerRequestError:
            self._write_json(
                400,
                {
                    "error_code": "invalid_planner_request",
                    "next_action": (
                        "Provide one technology UUID, valid_at, recorded_at, and a "
                        "planning horizon from 1 to 3650 days."
                    ),
                },
            )
            return
        try:
            decisions = reader(context, request)
        except Exception:
            self._write_json(
                503,
                {
                    "error_code": "planner_query_failed",
                    "next_action": (
                        "Keep the decision pending and retry after the EA query port "
                        "is healthy."
                    ),
                },
            )
            return
        self._write_json(
            200,
            {
                "technology_version_id": str(request.technology_version_id),
                "valid_at": request.valid_at.isoformat(),
                "recorded_at": request.recorded_at.isoformat(),
                "planning_horizon_days": request.planning_horizon_days,
                "decision_count": len(decisions),
                "decisions": list(decisions),
                "next_action": _next_plan_action(decisions),
            },
        )

    def _write_json(self, status: int, payload: Mapping[str, object]) -> None:
        """Write a JSON response an operator or buyer can act on immediately."""

        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        """Keep operator logs available without leaking request bodies or tokens."""

        super().log_message(format, *args)


def create_service_server(
    bind_address: BindAddress,
    *,
    contract_ready: bool = False,
    database_probe: ReadinessProbe | None = None,
    authorization_config: KeyverseAuthorizationConfig | None = None,
    jwks_loader: JwksLoader = load_keyverse_jwks,
    signature_verifier: SignatureVerifier = verify_rs256_signature,
    target_state_plan_reader: TargetStatePlanReader | None = None,
) -> ThreadingHTTPServer:
    """Create a bound server. Callers must shut it down after use."""

    server = ThreadingHTTPServer(
        (bind_address.bind_host, bind_address.bind_port),
        FoundationServiceHandler,
    )
    server.contract_ready = contract_ready
    server.database_probe = database_probe
    server.authorization_config = authorization_config
    server.jwks_loader = jwks_loader
    server.signature_verifier = signature_verifier
    server.target_state_plan_reader = target_state_plan_reader
    return server


def serve_forever(server: ThreadingHTTPServer) -> None:
    """Block until the server is shut down by the process supervisor."""

    server.serve_forever()


def main(argv: Sequence[str] | None = None) -> int:
    """Start the fail-closed runtime surface on ``0.0.0.0:$PORT``."""

    del argv
    environment: Mapping[str, str] = os.environ
    bind_address = resolve_bind_address(environ=environment)
    database_dsn = environment.get(_DATABASE_DSN_ENV)
    database_probe = build_database_readiness_probe(database_dsn)
    server = create_service_server(
        bind_address,
        contract_ready=probe_context_contract(),
        database_probe=database_probe,
        authorization_config=build_keyverse_authorization_config(environment),
        target_state_plan_reader=build_target_state_plan_reader(database_dsn),
    )
    try:
        serve_forever(server)
    except KeyboardInterrupt:
        return 0
    finally:
        server.server_close()
    return 0
