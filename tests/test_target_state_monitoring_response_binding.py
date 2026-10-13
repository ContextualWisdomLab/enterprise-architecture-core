"""Regression tests for exact monitoring response binding to buyer cutoffs."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

import ea_core_foundation.monitor as monitor
import ea_core_foundation.service as service
from tests.test_target_state_monitoring_api import _PATH, _context, _status


def _reader_for_status(**changes: object):
    """Return a monitoring reader backed by one controlled database response."""

    payload = _status(**changes)

    def runner(command, **kwargs):
        del command, kwargs
        return SimpleNamespace(
            returncode=0,
            stdout=json.dumps(payload),
            stderr="",
        )

    return monitor.build_target_state_monitoring_reader(
        "postgresql://ea_runtime@db.example/ea_core",
        runner=runner,
        base_environment={},
    )


@pytest.mark.parametrize(
    "changes",
    [
        {"verification_effective_at": "2027-03-02T00:00:00+00:00"},
        {"verification_recorded_at": "2027-03-02T00:00:00+00:00"},
        {"evidence_age_days": 26},
        {
            "monitoring_state_code": "stale",
            "next_action": "collect_new_target_state_evidence",
        },
    ],
)
def test_monitoring_reader_rejects_response_not_bound_to_requested_cutoffs(
    changes: dict[str, object],
) -> None:
    """Database output cannot override cutoffs, derived age, or freshness state."""

    request = monitor.parse_target_state_monitoring_request(_PATH)
    with pytest.raises(
        service.PlannerExecutionError,
        match="invalid monitoring status",
    ):
        _reader_for_status(**changes)(_context(), request)


@pytest.mark.parametrize(
    "changes",
    [
        {"monitoring_state_code": []},
        {"monitoring_state_code": {}},
        {"verification_state_code": []},
        {"verification_state_code": {}},
    ],
)
def test_monitoring_reader_fails_closed_on_non_scalar_state_codes(
    changes: dict[str, object],
) -> None:
    """Malformed database JSON cannot escape as an unhandled TypeError."""

    request = monitor.parse_target_state_monitoring_request(_PATH)
    with pytest.raises(
        service.PlannerExecutionError,
        match="invalid monitoring status",
    ):
        _reader_for_status(**changes)(_context(), request)
