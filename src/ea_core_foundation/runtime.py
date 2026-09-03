"""Extended runtime surface for governed target-state execution decisions."""

from __future__ import annotations

import os
from collections.abc import Callable, Mapping, Sequence
from http.server import ThreadingHTTPServer
from urllib.parse import urlparse

from .decision_plane_http import (
    BindAddress,
    FoundationServiceHandler,
    PlannerRequestError,
    ReadinessProbe,
    TargetStateApprovalWriter,
    TargetStatePlanReader,
    build_approval_authorization_config,
    build_database_readiness_probe,
    build_keyverse_authorization_config,
    build_target_state_approval_writer,
    build_target_state_plan_reader,
    probe_context_contract,
    resolve_bind_address,
    serve_forever,
)
from .identity_authorization.authorization import (
    AuthorizationContext,
    AuthorizationError,
    JwksLoader,
    KeyverseAuthorizationConfig,
    SignatureVerifier,
    load_keyverse_jwks,
    verify_keyverse_bearer,
    verify_rs256_signature,
)
from .strategy_transformation.schedule import (
    TargetStateScheduleRequest,
    TargetStateScheduleWriter,
    build_schedule_authorization_config,
    build_target_state_schedule_writer,
    parse_target_state_schedule_request,
)
from .strategy_transformation.start import (
    TargetStateStartRequest,
    build_start_authorization_config,
    build_target_state_start_writer,
    parse_target_state_start_request,
)

_TARGET_STATE_COMMAND_PATH_PREFIX = "/v1/architecture-transformations/"
_TARGET_STATE_SCHEDULE_PATH_SUFFIX = "/schedule"
_TARGET_STATE_START_PATH_SUFFIX = "/start"

TargetStateStartWriter = Callable[
    [AuthorizationContext, TargetStateStartRequest], Mapping[str, object]
]


class SchedulingServiceHandler(FoundationServiceHandler):
    """Extend the decision surface with governed schedule and start commands."""

    def _schedule_authorization_config(self) -> KeyverseAuthorizationConfig | None:
        """Return the distinct Keyverse schedule RP profile or fail closed."""

        config = getattr(self.server, "schedule_authorization_config", None)
        return config if isinstance(config, KeyverseAuthorizationConfig) else None

    def _schedule_writer(self):
        """Return the configured purpose-bound schedule writer."""

        writer = getattr(self.server, "target_state_schedule_writer", None)
        return writer if callable(writer) else None

    def _start_authorization_config(self) -> KeyverseAuthorizationConfig | None:
        """Return the distinct Keyverse start RP profile or fail closed."""

        config = getattr(self.server, "start_authorization_config", None)
        return config if isinstance(config, KeyverseAuthorizationConfig) else None

    def _start_writer(self):
        """Return the configured purpose-bound start writer."""

        writer = getattr(self.server, "target_state_start_writer", None)
        return writer if callable(writer) else None

    def do_POST(self) -> None:
        """Route execution commands and preserve inherited POST behavior."""

        normalized_path = urlparse(self.path).path
        if (
            normalized_path.startswith(_TARGET_STATE_COMMAND_PATH_PREFIX)
            and normalized_path.endswith(_TARGET_STATE_START_PATH_SUFFIX)
        ):
            self._serve_target_state_start()
            return
        if (
            normalized_path.startswith(_TARGET_STATE_COMMAND_PATH_PREFIX)
            and normalized_path.endswith(_TARGET_STATE_SCHEDULE_PATH_SUFFIX)
        ):
            self._serve_target_state_schedule()
            return
        super().do_POST()

    def _serve_target_state_schedule(self) -> None:
        """Authorize and atomically bind an approved transformation to a milestone."""

        config = self._schedule_authorization_config()
        writer = self._schedule_writer()
        if config is None or writer is None:
            self._write_json(
                503,
                {
                    "error_code": "schedule_unavailable",
                    "next_action": (
                        "Configure Keyverse schedule roles and the EA runtime database."
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
            request = parse_target_state_schedule_request(self.path, payload)
        except PlannerRequestError:
            self._write_json(
                400,
                {
                    "error_code": "invalid_schedule_request",
                    "next_action": (
                        "Send canonical UUIDv7 decision, milestone, and evidence ids, "
                        "effective_at, and a bounded decision reason as JSON."
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
                    "error_code": "schedule_command_failed",
                    "next_action": (
                        "Refresh the approved transformation and milestone evidence, "
                        "then retry with the same decision request id."
                    ),
                },
            )
            return
        status = 200 if receipt.get("replayed") is True else 201
        self._write_json(status, receipt)

    def _serve_target_state_start(self) -> None:
        """Authorize and atomically start one already-scheduled transformation."""

        config = self._start_authorization_config()
        writer = self._start_writer()
        if config is None or writer is None:
            self._write_json(
                503,
                {
                    "error_code": "start_unavailable",
                    "next_action": (
                        "Configure Keyverse start roles and the EA runtime database."
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
            request = parse_target_state_start_request(self.path, payload)
        except PlannerRequestError:
            self._write_json(
                400,
                {
                    "error_code": "invalid_start_request",
                    "next_action": (
                        "Send canonical UUIDv7 decision and evidence ids, "
                        "effective_at, and a bounded decision reason as JSON."
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
                    "error_code": "start_command_failed",
                    "next_action": (
                        "Refresh the approved schedule and transformation evidence, "
                        "then retry with the same decision request id."
                    ),
                },
            )
            return
        status = 200 if receipt.get("replayed") is True else 201
        self._write_json(status, receipt)


def create_runtime_server(
    bind_address: BindAddress,
    *,
    contract_ready: bool = False,
    database_probe: ReadinessProbe | None = None,
    authorization_config: KeyverseAuthorizationConfig | None = None,
    approval_authorization_config: KeyverseAuthorizationConfig | None = None,
    schedule_authorization_config: KeyverseAuthorizationConfig | None = None,
    start_authorization_config: KeyverseAuthorizationConfig | None = None,
    jwks_loader: JwksLoader = load_keyverse_jwks,
    signature_verifier: SignatureVerifier = verify_rs256_signature,
    target_state_plan_reader: TargetStatePlanReader | None = None,
    target_state_approval_writer: TargetStateApprovalWriter | None = None,
    target_state_schedule_writer: TargetStateScheduleWriter | None = None,
    target_state_start_writer: TargetStateStartWriter | None = None,
) -> ThreadingHTTPServer:
    """Create the deployable runtime with governed read and execution surfaces."""

    server = ThreadingHTTPServer(
        (bind_address.bind_host, bind_address.bind_port),
        SchedulingServiceHandler,
    )
    server.contract_ready = contract_ready
    server.database_probe = database_probe
    server.authorization_config = authorization_config
    server.approval_authorization_config = approval_authorization_config
    server.schedule_authorization_config = schedule_authorization_config
    server.start_authorization_config = start_authorization_config
    server.jwks_loader = jwks_loader
    server.signature_verifier = signature_verifier
    server.target_state_plan_reader = target_state_plan_reader
    server.target_state_approval_writer = target_state_approval_writer
    server.target_state_schedule_writer = target_state_schedule_writer
    server.target_state_start_writer = target_state_start_writer
    return server


def main(argv: Sequence[str] | None = None) -> int:
    """Start the deployable fail-closed decision runtime on ``0.0.0.0:$PORT``."""

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
        target_state_plan_reader=build_target_state_plan_reader(database_dsn),
        target_state_approval_writer=build_target_state_approval_writer(database_dsn),
        target_state_schedule_writer=build_target_state_schedule_writer(database_dsn),
        target_state_start_writer=build_target_state_start_writer(database_dsn),
    )
    try:
        serve_forever(server)
    except KeyboardInterrupt:
        return 0
    finally:
        server.server_close()
    return 0