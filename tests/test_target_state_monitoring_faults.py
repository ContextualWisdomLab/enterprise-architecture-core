"""Fail-closed acceptance for target-state monitoring input and database evidence."""

from __future__ import annotations

import json
import subprocess
from types import SimpleNamespace

import pytest

import ea_core_foundation.monitor as monitor
import ea_core_foundation.service as service
from tests.test_target_state_monitoring_api import (
    _EVIDENCE_ID,
    _PATH,
    _TRANSFORMATION_ID,
    _context,
    _status,
)


def _reader_for_payload(payload: object):
    """Build a monitoring reader returning one controlled PostgreSQL payload."""

    def runner(command, **kwargs):
        del command, kwargs
        stdout = payload if isinstance(payload, str) else json.dumps(payload)
        return SimpleNamespace(returncode=0, stdout=stdout, stderr="")

    return monitor.build_target_state_monitoring_reader(
        "postgresql://ea_runtime@db.example/ea_core",
        runner=runner,
        base_environment={},
    )


def test_monitoring_request_rejects_ambiguous_or_incomplete_routes() -> None:
    """Route identity and query meaning must remain singular and explicit."""

    invalid_paths = [
        "/v1/not-monitoring",
        (
            f"/v1/architecture-transformations/{_TRANSFORMATION_ID}/extra/monitoring"
            "?valid_at=2027-03-01T00:00:00Z&recorded_at=2027-03-01T00:00:00Z"
        ),
    ]
    for path in invalid_paths:
        with pytest.raises(service.PlannerRequestError):
            monitor.parse_target_state_monitoring_request(path)

    with pytest.raises(service.PlannerRequestError, match="duplicate"):
        monitor.parse_target_state_monitoring_request(
            _PATH + "&valid_at=2027-03-02T00:00:00Z"
        )
    with pytest.raises(service.PlannerRequestError, match="required"):
        monitor.parse_target_state_monitoring_request(
            f"/v1/architecture-transformations/{_TRANSFORMATION_ID}/monitoring"
            "?recorded_at=2027-03-01T00:00:00Z"
        )
    with pytest.raises(service.PlannerRequestError, match="integer"):
        monitor.parse_target_state_monitoring_request(
            _PATH.replace("max_evidence_age_days=90", "max_evidence_age_days=old")
        )

    default_age = monitor.parse_target_state_monitoring_request(
        _PATH.replace("&max_evidence_age_days=90", "")
    )
    assert default_age.max_evidence_age_days == 90


def test_monitoring_reader_fails_closed_when_connection_profile_is_invalid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A DSN that cannot become a safe isolated libpq environment is unavailable."""

    monkeypatch.setattr(monitor, "_postgres_environment", lambda dsn, env: None)
    reader = monitor.build_target_state_monitoring_reader("postgresql://invalid")
    with pytest.raises(service.PlannerExecutionError, match="unavailable"):
        reader(_context(), monitor.parse_target_state_monitoring_request(_PATH))


@pytest.mark.parametrize(
    "runner",
    [
        lambda command, **kwargs: (_ for _ in ()).throw(OSError("psql missing")),
        lambda command, **kwargs: (_ for _ in ()).throw(
            subprocess.TimeoutExpired(command, 10)
        ),
    ],
)
def test_monitoring_reader_maps_process_failures_to_one_safe_error(runner) -> None:
    """Process launch and timeout failures never leak command details as success."""

    reader = monitor.build_target_state_monitoring_reader(
        "postgresql://ea_runtime@db.example/ea_core",
        runner=runner,
        base_environment={},
    )
    with pytest.raises(service.PlannerExecutionError, match="command failed"):
        reader(_context(), monitor.parse_target_state_monitoring_request(_PATH))


def test_monitoring_reader_rejects_query_transport_and_json_failures() -> None:
    """Non-zero psql, malformed JSON, and non-object JSON all fail closed."""

    def nonzero(command, **kwargs):
        del command, kwargs
        return SimpleNamespace(returncode=2, stdout="", stderr="failure")

    reader = monitor.build_target_state_monitoring_reader(
        "postgresql://ea_runtime@db.example/ea_core",
        runner=nonzero,
        base_environment={},
    )
    request = monitor.parse_target_state_monitoring_request(_PATH)
    with pytest.raises(service.PlannerExecutionError, match="query failed"):
        reader(_context(), request)
    with pytest.raises(service.PlannerExecutionError, match="invalid JSON"):
        _reader_for_payload("not-json")(_context(), request)
    with pytest.raises(service.PlannerExecutionError, match="invalid monitoring status"):
        _reader_for_payload([])(_context(), request)


@pytest.mark.parametrize(
    "changes",
    [
        {"architecture_transformation_id": "0196e010-1111-7111-8111-111111111192"},
        {"verification_state_code": "proposed"},
        {"evidence_age_days": "27"},
        {"evidence_age_days": True},
        {"evidence_age_days": -1},
        {"monitoring_state_code": "unknown"},
        {"next_action": "done"},
        {
            "monitoring_state_code": "gap_detected",
            "verification_state_code": "verified",
            "next_action": "replan_target_state",
        },
        {
            "monitoring_state_code": "stale",
            "verification_state_code": "gap_detected",
            "next_action": "collect_new_target_state_evidence",
        },
    ],
)
def test_monitoring_reader_rejects_semantically_inconsistent_evidence(
    changes: dict[str, object],
) -> None:
    """Every returned identity, truth state, freshness value, and action is bound."""

    reader = _reader_for_payload(_status(**changes))
    with pytest.raises(service.PlannerExecutionError, match="invalid monitoring status"):
        reader(_context(), monitor.parse_target_state_monitoring_request(_PATH))


@pytest.mark.parametrize(
    "changes",
    [
        {"evidence_record_id": "not-a-uuid"},
        {"verification_effective_at": "not-a-time"},
        {"verification_recorded_at": "not-a-time"},
    ],
)
def test_monitoring_reader_rejects_invalid_evidence_identity_or_time(
    changes: dict[str, object],
) -> None:
    """Database evidence IDs and both temporal axes must remain canonical."""

    reader = _reader_for_payload(_status(**changes))
    with pytest.raises(service.PlannerExecutionError, match="invalid monitoring status"):
        reader(_context(), monitor.parse_target_state_monitoring_request(_PATH))


def test_monitoring_reader_accepts_all_defined_actionable_states() -> None:
    """Current, stale, and detected-gap states preserve distinct buyer actions."""

    cases = [
        ("current", "verified", "continue_monitoring"),
        ("stale", "verified", "collect_new_target_state_evidence"),
        ("gap_detected", "gap_detected", "replan_target_state"),
    ]
    request = monitor.parse_target_state_monitoring_request(_PATH)
    for state, verification_state, action in cases:
        result = _reader_for_payload(
            _status(
                monitoring_state_code=state,
                verification_state_code=verification_state,
                next_action=action,
            )
        )(_context(), request)
        assert result["next_action"] == action
        assert result["evidence_record_id"] == _EVIDENCE_ID
