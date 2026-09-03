"""Deployable HTTP runtime extension for target-state verification decisions."""

from __future__ import annotations

import os
from collections.abc import Mapping, Sequence
from http.server import ThreadingHTTPServer
from typing import Any
from urllib.parse import urlparse

from .completion_runtime import CompletionServiceHandler
from .completion_runtime import (
    create_runtime_server as create_completion_runtime_server,
)
from .decision_plane_http import (
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
from .identity_authorization.authorization import (
    AuthorizationError,
    KeyverseAuthorizationConfig,
    load_keyverse_jwks,
    verify_keyverse_bearer,
    verify_rs256_signature,
)
from .runtime import (
    build_schedule_authorization_config,
    build_target_state_schedule_writer,
)
from .strategy_transformation.complete import (
    build_complete_authorization_config,
    build_target_state_complete_writer,
)
from .strategy_transformation.start import (
    build_start_authorization_config,
    build_target_state_start_writer,
)
from .verify import (
    build_target_state_verification_writer,
    build_verification_authorization_config,
    parse_target_state_verification_request,
)

_TARGET_STATE_COMMAND_PATH_PREFIX = "/v1/architecture-transformations/"
_TARGET_STATE_VERIFICATION_PATH_SUFFIX = "/verification"


class VerificationServiceHandler(CompletionServiceHandler):
    """Add target-state verification while preserving prior execution routes."""

    def _verification_authorization_config(
        self,
    ) -> KeyverseAuthorizationConfig | None:
        """Return the distinct Keyverse verification profile or fail closed."""

        config = getattr(self.server, "verification_authorization_config", None)
        return config if isinstance(config, KeyverseAuthorizationConfig) else None

    def _verification_writer(self):
        """Return the configured purpose-bound verification writer."""

        writer = getattr(self.server, "target_state_verification_writer", None)
        return writer if callable(writer) else None

    def do_POST(self) -> None:
        """Route verification first and delegate every earlier command unchanged."""

        normalized_path = urlparse(self.path).path
        if (
            normalized_path.startswith(_TARGET_STATE_COMMAND_PATH_PREFIX)
            and normalized_path.endswith(_TARGET_STATE_VERIFICATION_PATH_SUFFIX)
        ):
            self._serve_target_state_verification()
            return
        super().do_POST()

    def _serve_target_state_verification(self) -> None:
        """Authorize and atomically verify one completed target-state outcome."""

        config = self._verification_authorization_config()
        writer = self._verification_writer()
        if config is None or writer is None:
            self._write_json(
                503,
                {
                    "error_code": "verification_unavailable",
                    "next_action": (
                        "Configure Keyverse target-state verification roles and "
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
            request = parse_target_state_verification_request(self.path, payload)
        except PlannerRequestError:
            self._write_json(
                400,
                {
                    "error_code": "invalid_verification_request",
                    "next_action": (
                        "Send canonical UUIDv7 decision/evidence ids, effective_at, "
                        "a bounded reason, and verified or gap_detected outcome."
                    ),
                },
            )
            return
        try:
            receipt = writer(context, request)
        except PlannerExecutionError:
            self._write_json(
                503,
                {
                    "error_code": "verification_command_failed",
                    "next_action": (
                        "Refresh the completed transformation and target-state "
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
    verification_authorization_config: KeyverseAuthorizationConfig | None = None,
    target_state_verification_writer: Any = None,
    **runtime_kwargs: Any,
) -> ThreadingHTTPServer:
    """Create the complete runtime plus purpose-bound verification behavior."""

    server = create_completion_runtime_server(bind_address, **runtime_kwargs)
    server.RequestHandlerClass = VerificationServiceHandler
    server.verification_authorization_config = verification_authorization_config
    server.target_state_verification_writer = target_state_verification_writer
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
        target_state_plan_reader=build_target_state_plan_reader(database_dsn),
        target_state_approval_writer=build_target_state_approval_writer(database_dsn),
        target_state_schedule_writer=build_target_state_schedule_writer(database_dsn),
        target_state_start_writer=build_target_state_start_writer(database_dsn),
        target_state_complete_writer=build_target_state_complete_writer(database_dsn),
        target_state_verification_writer=(
            build_target_state_verification_writer(database_dsn)
        ),
    )
    try:
        serve_forever(server)
    except KeyboardInterrupt:
        return 0
    finally:
        server.server_close()
    return 0
