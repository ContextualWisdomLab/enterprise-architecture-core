"""Extended runtime surface for governed target-state execution decisions."""

from __future__ import annotations

import os
from collections.abc import Mapping, Sequence
from http.server import ThreadingHTTPServer

from .decision_plane_http import (
    BindAddress,
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
    JwksLoader,
    KeyverseAuthorizationConfig,
    SignatureVerifier,
    load_keyverse_jwks,
    verify_rs256_signature,
)
from .strategy_transformation.http import (
    SchedulingServiceHandler,
    TargetStateStartWriter,
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
