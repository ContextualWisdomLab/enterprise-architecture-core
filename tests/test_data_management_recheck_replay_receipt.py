"""RED acceptance for observable reassessment idempotency semantics."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from ea_core_foundation.data_management_recheck import (
    build_data_management_recheck_writer,
    parse_data_management_recheck_request,
)
from ea_core_foundation.service import PlannerExecutionError
from tests.test_data_management_recheck_api import _PATH, _context, _payload, _receipt
from tests.test_data_management_recheck_runtime import _recheck_config
from tests.test_target_state_replan_runtime import (
    _jwks_loader,
    _post,
    _start_server,
    _stop_server,
    _token,
)

_RECHECK_ROLE = "ea_data_management_rechecker"


def _stdout_runner(payload: dict[str, object]):
    """Return one successful psql-shaped runner for the supplied receipt."""

    def runner(command, **kwargs):
        del command, kwargs
        return SimpleNamespace(returncode=0, stdout=json.dumps(payload), stderr="")

    return runner


def test_writer_accepts_only_boolean_replay_evidence() -> None:
    """The command receipt tells an operator whether the durable write was replayed."""

    request = parse_data_management_recheck_request(_PATH, _payload())
    writer = build_data_management_recheck_writer(
        "postgresql://ea_runtime@db.example/ea_core",
        runner=_stdout_runner(_receipt(replayed=False)),
    )

    result = writer(_context(), request)

    assert result["replayed"] is False

    invalid_writer = build_data_management_recheck_writer(
        "postgresql://ea_runtime@db.example/ea_core",
        runner=_stdout_runner(_receipt(replayed="false")),
    )
    with pytest.raises(PlannerExecutionError, match="invalid reassessment receipt"):
        invalid_writer(_context(), request)


def test_http_distinguishes_creation_from_exact_replay() -> None:
    """A new durable request returns 201 while an exact retry returns 200."""

    for replayed, expected_status in ((False, 201), (True, 200)):
        server, thread, host, port = _start_server(
            data_management_recheck_authorization_config=_recheck_config(),
            jwks_loader=_jwks_loader,
            signature_verifier=lambda signing_input, signature, jwk: True,
            data_management_recheck_writer=(
                lambda context, request, replayed=replayed: _receipt(
                    replayed=replayed
                )
            ),
        )
        try:
            status, body = _post(
                host,
                port,
                authorization=f"Bearer {_token(_RECHECK_ROLE)}",
                path=_PATH,
                payload=_payload(),
            )
        finally:
            _stop_server(server, thread)

        assert status == expected_status
        assert body["replayed"] is replayed
        assert body["next_action"] == "await_assessment_recheck"
