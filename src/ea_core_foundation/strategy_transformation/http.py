"""HTTP adapter for Strategy & Transformation commands."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from urllib.parse import urlparse

from ..decision_plane_http import FoundationServiceHandler, PlannerRequestError
from ..identity_authorization.authorization import (
    AuthorizationContext,
    AuthorizationError,
    KeyverseAuthorizationConfig,
    load_keyverse_jwks,
    verify_keyverse_bearer,
    verify_rs256_signature,
)
from .schedule import TargetStateScheduleRequest, parse_target_state_schedule_request
from .start import TargetStateStartRequest, parse_target_state_start_request

_TARGET_STATE_COMMAND_PATH_PREFIX = "/v1/architecture-transformations/"
_TARGET_STATE_SCHEDULE_PATH_SUFFIX = "/schedule"
_TARGET_STATE_START_PATH_SUFFIX = "/start"

TargetStateStartWriter = Callable[
    [AuthorizationContext, TargetStateStartRequest], Mapping[str, object]
]


class SchedulingServiceHandler(FoundationServiceHandler):
    """Expose purpose-bound schedule and start commands over the EA HTTP surface."""

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
        """Route transformation commands and preserve inherited POST behavior."""

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
