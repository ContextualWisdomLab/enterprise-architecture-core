"""Deployable HTTP runtime extension for target-state monitoring decisions."""

from __future__ import annotations

import os
from collections.abc import Mapping, Sequence
from http.server import ThreadingHTTPServer
from typing import Any
from urllib.parse import urlparse

from .authorization import (
    AuthorizationError,
    KeyverseAuthorizationConfig,
    load_keyverse_jwks,
    verify_keyverse_bearer,
    verify_rs256_signature,
)
from .complete import (
    build_complete_authorization_config,
    build_target_state_complete_writer,
)
from .monitor import (
    build_monitoring_authorization_config,
    build_target_state_monitoring_reader,
    parse_target_state_monitoring_request,
)
from .runtime import (
    build_schedule_authorization_config,
    build_target_state_schedule_writer,
)
from .service import (
    BindAddress,
    PlannerExecutionError,
    PlannerRequestError,
    build_approval_authorization_config,
    build_database_readiness_probe,
    build_keyverse_authorization_config,
    build_target_state_approval_writer,
    build_target_state_plan_reader,
    probe_context_contract,
    resolve_bind_address,
    serve_forever,
)
from .start import build_start_authorization_config, build_target_state_start_writer
from .verification_runtime import VerificationServiceHandler
from .verification_runtime import (
    create_runtime_server as create_verification_runtime_server,
)
from .verify import (
    build_target_state_verification_writer,
    build_verification_authorization_config,
)

_TARGET_STATE_MONITORING_PATH_PREFIX = "/v1/architecture-transformations/"
_TARGET_STATE_MONITORING_PATH_SUFFIX = "/monitoring"


class MonitoringServiceHandler(VerificationServiceHandler):
    """Add monitoring reads while preserving every governed earlier route."""

    def _monitoring_authorization_config(
        self,
    ) -> KeyverseAuthorizationConfig | None:
        """Return the distinct Keyverse monitoring profile or fail closed."""

        config = getattr(self.server, "monitoring_authorization_config", None)
        return config if isinstance(config, KeyverseAuthorizationConfig) else None

    def _monitoring_reader(self):
        """Return the configured purpose-bound monitoring reader."""

        reader = getattr(self.server, "target_state_monitoring_reader", None)
        return reader if callable(reader) else None

    def do_GET(self) -> None:
        """Route monitoring first and delegate every earlier GET unchanged."""

        normalized_path = urlparse(self.path).path
        if (
            normalized_path.startswith(_TARGET_STATE_MONITORING_PATH_PREFIX)
            and normalized_path.endswith(_TARGET_STATE_MONITORING_PATH_SUFFIX)
        ):
            self._serve_target_state_monitoring()
            return
        super().do_GET()

    def _serve_target_state_monitoring(self) -> None:
        """Authorize and return one exact verification-evidence freshness decision."""

        config = self._monitoring_authorization_config()
        reader = self._monitoring_reader()
        if config is None or reader is None:
            self._write_json(
                503,
                {
                    "error_code": "monitoring_unavailable",
                    "next_action": (
                        "Configure Keyverse target-state monitoring roles and the "
                        "EA runtime database."
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
                {"error_code": error.error_code, "next_action": error.next_action},
            )
            return
        try:
            request = parse_target_state_monitoring_request(self.path)
        except PlannerRequestError:
            self._write_json(
                400,
                {
                    "error_code": "invalid_monitoring_request",
                    "next_action": (
                        "Provide one canonical UUIDv7 transformation identifier, "
                        "valid_at, recorded_at, and an evidence age from 1 to 3650 days."
                    ),
                },
            )
            return
        try:
            status = reader(context, request)
        except PlannerExecutionError:
            self._write_json(
                503,
                {
                    "error_code": "monitoring_query_failed",
                    "next_action": (
                        "Keep the target state under review and retry after the EA "
                        "monitoring read port is healthy."
                    ),
                },
            )
            return
        self._write_json(200, status)


def create_runtime_server(
    bind_address: BindAddress,
    *,
    monitoring_authorization_config: KeyverseAuthorizationConfig | None = None,
    target_state_monitoring_reader: Any = None,
    **runtime_kwargs: Any,
) -> ThreadingHTTPServer:
    """Create the verification runtime plus target-state monitoring behavior."""

    server = create_verification_runtime_server(bind_address, **runtime_kwargs)
    server.RequestHandlerClass = MonitoringServiceHandler
    server.monitoring_authorization_config = monitoring_authorization_config
    server.target_state_monitoring_reader = target_state_monitoring_reader
    return server


def main(argv: Sequence[str] | None = None) -> int:
    """Start the complete governed EA decision runtime on ``0.0.0.0:$PORT``."""

    del argv
    environment: Mapping[str, str] = os.environ
    bind_address = resolve_bind_address(environ=environment)
    database_dsn = environment.get("EA_DATABASE_DSN")
    server = create_runtime_server(
        bind_address,
        contract_ready=probe_context_contract(),
        database_probe=build_database_readiness_probe(database_dsn),
        authorization_config=build_keyverse_authorization_config(environment),
        approval_authorization_config=build_approval_authorization_config(environment),
        schedule_authorization_config=build_schedule_authorization_config(environment),
        start_authorization_config=build_start_authorization_config(environment),
        complete_authorization_config=build_complete_authorization_config(environment),
        verification_authorization_config=(
            build_verification_authorization_config(environment)
        ),
        monitoring_authorization_config=(
            build_monitoring_authorization_config(environment)
        ),
        target_state_plan_reader=build_target_state_plan_reader(database_dsn),
        target_state_approval_writer=build_target_state_approval_writer(database_dsn),
        target_state_schedule_writer=build_target_state_schedule_writer(database_dsn),
        target_state_start_writer=build_target_state_start_writer(database_dsn),
        target_state_complete_writer=build_target_state_complete_writer(database_dsn),
        target_state_verification_writer=(
            build_target_state_verification_writer(database_dsn)
        ),
        target_state_monitoring_reader=(
            build_target_state_monitoring_reader(database_dsn)
        ),
    )
    try:
        serve_forever(server)
    except KeyboardInterrupt:
        return 0
    finally:
        server.server_close()
    return 0
