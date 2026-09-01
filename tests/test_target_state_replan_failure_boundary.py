"""Regression coverage for the HTTP replanning failure boundary."""

from __future__ import annotations

from typing import Any

from tests.test_target_state_replan_runtime import (
    _config,
    _jwks_loader,
    _post,
    _start_server,
    _stop_server,
    _token,
)


def test_http_replan_fails_closed_on_unexpected_writer_exception() -> None:
    """Unexpected command-port faults must return a stable retryable response."""

    def exploding_writer(context: Any, request: Any) -> dict[str, object]:
        del context, request
        raise RuntimeError("unexpected database adapter failure")

    server, thread, host, port = _start_server(
        replan_authorization_config=_config(),
        jwks_loader=_jwks_loader,
        signature_verifier=lambda signing_input, signature, jwk: True,
        target_state_replan_writer=exploding_writer,
    )
    try:
        status, body = _post(
            host,
            port,
            authorization=f"Bearer {_token()}",
        )
    finally:
        _stop_server(server, thread)

    assert status == 503
    assert body["error_code"] == "replan_command_failed"
    assert "retry" in body["next_action"].lower()
