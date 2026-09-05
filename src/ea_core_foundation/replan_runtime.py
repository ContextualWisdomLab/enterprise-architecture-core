"""Deployable HTTP runtime for governed EA replanning and reassessment commands."""

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
from .data_management_recheck import (
    build_data_management_recheck_authorization_config,
    build_data_management_recheck_writer,
    parse_data_management_recheck_request,
)
from .monitor import (
    build_monitoring_authorization_config,
    build_target_state_monitoring_reader,
)
from .monitoring_runtime import MonitoringServiceHandler
from .monitoring_runtime import (
    create_runtime_server as create_monitoring_runtime_server,
)
from .replan import (
    build_replan_authorization_config,
    build_target_state_replan_writer,
    parse_target_state_replan_request,
)
from .runtime import (
    build_schedule_authorization_config,
    build_target_state_schedule_writer,
)
from .service import (
    BindAddress,
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
from .verify import (
    build_target_state_verification_writer,
    build_verification_authorization_config,
)

_TARGET_STATE_COMMAND_PATH_PREFIX = "/v1/architecture-transformations/"
_TARGET_STATE_REPLAN_PATH_SUFFIX = "/replan"
_DATA_MANAGEMENT_RECHECK_PATH_PREFIX = "/v1/data-management-assessments/"
_DATA_MANAGEMENT_RECHECK_PATH_SUFFIX = "/recheck"


class ReplanServiceHandler(MonitoringServiceHandler):
    """Add governed replanning and reassessment writes to the complete runtime."""

    def _replan_authorization_config(self) -> KeyverseAuthorizationConfig | None:
        """Return the distinct Keyverse replanning profile or fail closed."""

        config = getattr(self.server, "replan_authorization_config", None)
        return config if isinstance(config, KeyverseAuthorizationConfig) else None

    def _replan_writer(self):
        """Return the configured purpose-bound replanning writer."""

        writer = getattr(self.server, "target_state_replan_writer", None)
        return writer if callable(writer) else None

    def _data_management_recheck_authorization_config(
        self,
    ) -> KeyverseAuthorizationConfig | None:
        """Return the distinct Keyverse reassessment profile or fail closed."""

        config = getattr(
            self.server,
            "data_management_recheck_authorization_config",
            None,
        )
        return config if isinstance(config, KeyverseAuthorizationConfig) else None

    def _data_management_recheck_writer(self):
        """Return the configured purpose-bound reassessment writer."""

        writer = getattr(self.server, "data_management_recheck_writer", None)
        return writer if callable(writer) else None

    def do_POST(self) -> None:
        """Route terminal command extensions before delegating earlier commands."""

        request_target = self.requestline.split(" ", 2)[1]
        normalized_path = urlparse(request_target).path
        if (
            normalized_path.startswith(_DATA_MANAGEMENT_RECHECK_PATH_PREFIX)
            and normalized_path.endswith(_DATA_MANAGEMENT_RECHECK_PATH_SUFFIX)
        ):
            self._serve_data_management_recheck(request_target)
            return
        if (
            normalized_path.startswith(_TARGET_STATE_COMMAND_PATH_PREFIX)
            and normalized_path.endswith(_TARGET_STATE_REPLAN_PATH_SUFFIX)
        ):
            self._serve_target_state_replan(request_target)
            return
        super().do_POST()

    def _serve_data_management_recheck(self, request_target: str) -> None:
        """Authorize and atomically request one evidence-backed reassessment."""

        config = self._data_management_recheck_authorization_config()
        writer = self._data_management_recheck_writer()
        if config is None or writer is None:
            self._write_json(
                503,
                {
                    "error_code": "data_management_recheck_unavailable",
                    "next_action": (
                        "Configure Keyverse data-management reassessment roles and "
                        "the EA runtime database."
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
            payload = self._read_approval_json()
            request = parse_data_management_recheck_request(request_target, payload)
        except PlannerRequestError:
            self._write_json(
                400,
                {
                    "error_code": "invalid_data_management_recheck_request",
                    "next_action": (
                        "Send canonical UUIDv7 acceptance and decision ids with "
                        "the requested_at timestamp for this assessment projection."
                    ),
                },
            )
            return
        try:
            receipt = writer(context, request)
        except Exception:
            self._write_json(
                503,
                {
                    "error_code": "data_management_recheck_command_failed",
                    "next_action": (
                        "Refresh the evidence-closed assessment and retry the same "
                        "decision request id."
                    ),
                },
            )
            return
        status = 200 if receipt.get("replayed") is True else 201
        self._write_json(status, receipt)

    def _serve_target_state_replan(self, request_target: str) -> None:
        """Authorize and atomically record one governed replacement target state."""

        config = self._replan_authorization_config()
        writer = self._replan_writer()
        if config is None or writer is None:
            self._write_json(
                503,
                {
                    "error_code": "replan_unavailable",
                    "next_action": (
                        "Configure Keyverse target-state replanning roles and the "
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
            payload = self._read_approval_json()
            request = parse_target_state_replan_request(request_target, payload)
        except PlannerRequestError:
            self._write_json(
                400,
                {
                    "error_code": "invalid_replan_request",
                    "next_action": (
                        "Send canonical UUIDv7 replacement, decision, scenario, "
                        "initiative, and evidence ids with bounded target-state "
                        "meaning, effective_at, and a human decision reason."
                    ),
                },
            )
            return
        try:
            receipt = writer(context, request)
        except Exception:
            self._write_json(
                503,
                {
                    "error_code": "replan_command_failed",
                    "next_action": (
                        "Refresh the gap-detected predecessor and supporting "
                        "evidence, then retry the same decision request id."
                    ),
                },
            )
            return
        status = 200 if receipt.get("replayed") is True else 201
        self._write_json(status, receipt)


def create_runtime_server(
    bind_address: BindAddress,
    *,
    replan_authorization_config: KeyverseAuthorizationConfig | None = None,
    target_state_replan_writer: Any = None,
    data_management_recheck_authorization_config: (
        KeyverseAuthorizationConfig | None
    ) = None,
    data_management_recheck_writer: Any = None,
    **runtime_kwargs: Any,
) -> ThreadingHTTPServer:
    """Create the complete runtime plus purpose-bound terminal command behavior."""

    server = create_monitoring_runtime_server(bind_address, **runtime_kwargs)
    server.RequestHandlerClass = ReplanServiceHandler
    server.replan_authorization_config = replan_authorization_config
    server.target_state_replan_writer = target_state_replan_writer
    server.data_management_recheck_authorization_config = (
        data_management_recheck_authorization_config
    )
    server.data_management_recheck_writer = data_management_recheck_writer
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
        replan_authorization_config=build_replan_authorization_config(environment),
        data_management_recheck_authorization_config=(
            build_data_management_recheck_authorization_config(environment)
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
        target_state_replan_writer=build_target_state_replan_writer(database_dsn),
        data_management_recheck_writer=build_data_management_recheck_writer(
            database_dsn
        ),
    )
    try:
        serve_forever(server)
    except KeyboardInterrupt:
        return 0
    finally:
        server.server_close()
    return 0
