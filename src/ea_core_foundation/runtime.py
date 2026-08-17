"""Extended runtime surface for governed target-state execution decisions."""

from __future__ import annotations

import json
import os
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from http.server import ThreadingHTTPServer
from typing import cast
from urllib.parse import urlparse
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
from .service import (
    BindAddress,
    CommandRunner,
    FoundationServiceHandler,
    PlannerExecutionError,
    PlannerRequestError,
    ReadinessProbe,
    TargetStateApprovalWriter,
    TargetStatePlanReader,
    _parse_timestamp,
    _parse_uuid7,
    _postgres_environment,
    build_approval_authorization_config,
    build_database_readiness_probe,
    build_target_state_approval_writer,
    build_target_state_plan_reader,
    probe_context_contract,
    resolve_bind_address,
    serve_forever,
)

_TARGET_STATE_COMMAND_PATH_PREFIX = "/v1/architecture-transformations/"
_TARGET_STATE_SCHEDULE_PATH_SUFFIX = "/schedule"
_SCHEDULE_ACTOR_ENV = "EA_SCHEDULE_ACTOR_REF"
_SCHEDULE_REASON_ENV = "EA_SCHEDULE_REASON_TEXT"
_TARGET_STATE_SCHEDULE_SQL = """
SELECT row_to_json(schedule_receipt)::text
FROM (
    SELECT
        schedule.transformation_schedule_record_id,
        schedule.architecture_transformation_id,
        schedule.initiative_milestone_id,
        schedule.outbox_event_id,
        schedule.decision_request_id,
        schedule.milestone_target_at,
        schedule.schedule_recorded_at,
        schedule.schedule_replayed AS replayed,
        schedule.next_action
    FROM architecture_core.schedule_transformation(
        :'tenant_record_id'::uuid,
        :'architecture_transformation_id'::uuid,
        :'decision_request_id'::uuid,
        :'initiative_milestone_id'::uuid,
        :'effective_at'::timestamptz,
        :'decision_actor_ref'::text,
        :'decision_reason_text'::text,
        :'evidence_record_id'::uuid
    ) AS schedule
) AS schedule_receipt;
""".strip()


@dataclass(frozen=True, slots=True)
class TargetStateScheduleRequest:
    """One immutable decision binding an approved transformation to a milestone."""

    architecture_transformation_id: UUID
    decision_request_id: UUID
    initiative_milestone_id: UUID
    effective_at: datetime
    decision_reason_text: str
    evidence_record_id: UUID

    @classmethod
    def from_values(
        cls,
        architecture_transformation_id: str,
        decision_request_id: str,
        initiative_milestone_id: str,
        effective_at: str,
        decision_reason_text: str,
        evidence_record_id: str,
    ) -> TargetStateScheduleRequest:
        """Validate one schedule command before verified authority reaches PostgreSQL."""

        transformation_id = _parse_uuid7(
            architecture_transformation_id,
            "architecture transformation id",
        )
        request_id = _parse_uuid7(decision_request_id, "decision request id")
        milestone_id = _parse_uuid7(initiative_milestone_id, "initiative milestone id")
        evidence_id = _parse_uuid7(evidence_record_id, "evidence record id")
        effective_time = _parse_timestamp(effective_at, "effective_at")
        reason = decision_reason_text.strip()
        if not reason or len(reason) > 4096:
            raise PlannerRequestError(
                "decision_reason_text must contain between 1 and 4096 characters"
            )
        return cls(
            architecture_transformation_id=transformation_id,
            decision_request_id=request_id,
            initiative_milestone_id=milestone_id,
            effective_at=effective_time,
            decision_reason_text=reason,
            evidence_record_id=evidence_id,
        )


TargetStateScheduleWriter = callable


def parse_target_state_schedule_request(
    path: str,
    payload: Mapping[str, object],
) -> TargetStateScheduleRequest:
    """Bind strict JSON to the one transformation named by the schedule path."""

    parsed = urlparse(path)
    if parsed.query or parsed.fragment:
        raise PlannerRequestError("schedule path cannot contain query or fragment data")
    route = parsed.path
    if (
        not route.startswith(_TARGET_STATE_COMMAND_PATH_PREFIX)
        or not route.endswith(_TARGET_STATE_SCHEDULE_PATH_SUFFIX)
    ):
        raise PlannerRequestError("target-state schedule path is invalid")
    prefix_length = len(_TARGET_STATE_COMMAND_PATH_PREFIX)
    suffix_length = len(_TARGET_STATE_SCHEDULE_PATH_SUFFIX)
    transformation_id = route[prefix_length:-suffix_length]
    if not transformation_id or "/" in transformation_id:
        raise PlannerRequestError(
            "target-state schedule requires one transformation UUID"
        )
    required_names = {
        "decision_request_id",
        "initiative_milestone_id",
        "effective_at",
        "decision_reason_text",
        "evidence_record_id",
    }
    if set(payload) != required_names:
        raise PlannerRequestError(
            "schedule body must contain only the documented fields"
        )
    if not all(isinstance(payload[name], str) for name in required_names):
        raise PlannerRequestError("schedule fields must be JSON strings")
    return TargetStateScheduleRequest.from_values(
        transformation_id,
        str(payload["decision_request_id"]),
        str(payload["initiative_milestone_id"]),
        str(payload["effective_at"]),
        str(payload["decision_reason_text"]),
        str(payload["evidence_record_id"]),
    )


def build_schedule_authorization_config(
    environ: Mapping[str, str],
) -> KeyverseAuthorizationConfig | None:
    """Build a Keyverse RP profile whose roles grant only scheduling authority."""

    schedule_environment = dict(environ)
    schedule_environment["EA_READ_ROLES"] = environ.get("EA_SCHEDULE_ROLES", "")
    return build_keyverse_authorization_config(schedule_environment)


def _unavailable_schedule_writer(
    context: AuthorizationContext,
    request: TargetStateScheduleRequest,
) -> Mapping[str, object]:
    """Reject scheduling when no safe PostgreSQL command port is configured."""

    del context, request
    raise PlannerExecutionError("target-state schedule database is unavailable")


def build_target_state_schedule_writer(
    dsn: str | None,
    *,
    runner: CommandRunner = subprocess.run,
    base_environment: Mapping[str, str] | None = None,
):
    """Build the purpose-bound scheduler without granting direct table mutation."""

    if not dsn:
        return _unavailable_schedule_writer
    connection_environment = _postgres_environment(dsn, base_environment)
    if connection_environment is None:
        return _unavailable_schedule_writer

    def writer(
        context: AuthorizationContext,
        request: TargetStateScheduleRequest,
    ) -> Mapping[str, object]:
        """Execute one idempotent milestone binding through the governed DB function."""

        actor_ref = f"keyverse:{context.issuer_uri}#{context.subject_id}"
        if len(actor_ref) > 2048:
            raise PlannerExecutionError("verified actor reference is too long")
        schedule_environment = dict(connection_environment)
        schedule_environment[_SCHEDULE_ACTOR_ENV] = actor_ref
        schedule_environment[_SCHEDULE_REASON_ENV] = request.decision_reason_text
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
            f"architecture_transformation_id={request.architecture_transformation_id}",
            "--set",
            f"decision_request_id={request.decision_request_id}",
            "--set",
            f"initiative_milestone_id={request.initiative_milestone_id}",
            "--set",
            f"effective_at={request.effective_at.isoformat()}",
            "--set",
            f"evidence_record_id={request.evidence_record_id}",
            "--command",
            r"\getenv decision_actor_ref EA_SCHEDULE_ACTOR_REF",
            "--command",
            r"\getenv decision_reason_text EA_SCHEDULE_REASON_TEXT",
            "--command",
            _TARGET_STATE_SCHEDULE_SQL,
        ]
        try:
            result = runner(
                command,
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
                env=schedule_environment,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            raise PlannerExecutionError(
                "target-state schedule database command failed"
            ) from error
        if result.returncode != 0:
            raise PlannerExecutionError("target-state schedule database query failed")
        try:
            payload = json.loads(result.stdout.strip())
        except json.JSONDecodeError as error:
            raise PlannerExecutionError(
                "target-state schedule returned invalid JSON"
            ) from error
        if not isinstance(payload, Mapping):
            raise PlannerExecutionError("target-state schedule returned invalid schedule receipt")
        try:
            _parse_uuid7(
                cast(str, payload.get("transformation_schedule_record_id")),
                "transformation schedule record id",
            )
            _parse_timestamp(
                cast(str, payload.get("milestone_target_at")),
                "milestone_target_at",
            )
            _parse_timestamp(
                cast(str, payload.get("schedule_recorded_at")),
                "schedule_recorded_at",
            )
        except PlannerRequestError as error:
            raise PlannerExecutionError(
                "target-state schedule returned invalid schedule receipt"
            ) from error
        if (
            payload.get("architecture_transformation_id")
            != str(request.architecture_transformation_id)
            or payload.get("initiative_milestone_id")
            != str(request.initiative_milestone_id)
            or payload.get("decision_request_id") != str(request.decision_request_id)
            or not isinstance(payload.get("replayed"), bool)
            or payload.get("next_action") != "start_transformation"
        ):
            raise PlannerExecutionError(
                "target-state schedule returned invalid schedule receipt"
            )
        return payload

    return writer


class SchedulingServiceHandler(FoundationServiceHandler):
    """Extend the existing decision surface with one governed schedule command."""

    def _schedule_authorization_config(self) -> KeyverseAuthorizationConfig | None:
        """Return the distinct Keyverse schedule RP profile or fail closed."""

        config = getattr(self.server, "schedule_authorization_config", None)
        return config if isinstance(config, KeyverseAuthorizationConfig) else None

    def _schedule_writer(self):
        """Return the configured purpose-bound schedule writer."""

        writer = getattr(self.server, "target_state_schedule_writer", None)
        return writer if callable(writer) else None

    def do_POST(self) -> None:
        """Route the schedule command and preserve all inherited POST behavior."""

        normalized_path = urlparse(self.path).path
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


def create_runtime_server(
    bind_address: BindAddress,
    *,
    contract_ready: bool = False,
    database_probe: ReadinessProbe | None = None,
    authorization_config: KeyverseAuthorizationConfig | None = None,
    approval_authorization_config: KeyverseAuthorizationConfig | None = None,
    schedule_authorization_config: KeyverseAuthorizationConfig | None = None,
    jwks_loader: JwksLoader = load_keyverse_jwks,
    signature_verifier: SignatureVerifier = verify_rs256_signature,
    target_state_plan_reader: TargetStatePlanReader | None = None,
    target_state_approval_writer: TargetStateApprovalWriter | None = None,
    target_state_schedule_writer=None,
) -> ThreadingHTTPServer:
    """Create the deployable runtime with read, approval, and scheduling surfaces."""

    server = ThreadingHTTPServer(
        (bind_address.bind_host, bind_address.bind_port),
        SchedulingServiceHandler,
    )
    server.contract_ready = contract_ready
    server.database_probe = database_probe
    server.authorization_config = authorization_config
    server.approval_authorization_config = approval_authorization_config
    server.schedule_authorization_config = schedule_authorization_config
    server.jwks_loader = jwks_loader
    server.signature_verifier = signature_verifier
    server.target_state_plan_reader = target_state_plan_reader
    server.target_state_approval_writer = target_state_approval_writer
    server.target_state_schedule_writer = target_state_schedule_writer
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
        target_state_plan_reader=build_target_state_plan_reader(database_dsn),
        target_state_approval_writer=build_target_state_approval_writer(database_dsn),
        target_state_schedule_writer=build_target_state_schedule_writer(database_dsn),
    )
    try:
        serve_forever(server)
    except KeyboardInterrupt:
        return 0
    finally:
        server.server_close()
    return 0
