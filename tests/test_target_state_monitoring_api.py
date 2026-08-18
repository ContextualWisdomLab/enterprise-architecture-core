"""Test-first contract for monitoring an evidence-backed verified target state."""

from __future__ import annotations

import json
from types import SimpleNamespace
from uuid import UUID

import pytest

from ea_core_foundation.authorization import AuthorizationContext
from ea_core_foundation.monitor import (
    TargetStateMonitoringRequest,
    build_monitoring_authorization_config,
    build_target_state_monitoring_reader,
    parse_target_state_monitoring_request,
)
from ea_core_foundation.service import PlannerExecutionError, PlannerRequestError

_TRANSFORMATION_ID = "0196e010-1111-7111-8111-111111111191"
_EVIDENCE_ID = "0195d145-64e8-7f4f-8a23-a0cc784cbf10"
_PATH = (
    f"/v1/architecture-transformations/{_TRANSFORMATION_ID}/monitoring"
    "?valid_at=2027-03-01T00:00:00Z"
    "&recorded_at=2027-03-01T00:00:00Z"
    "&max_evidence_age_days=90"
)


def _context() -> AuthorizationContext:
    """Return one already-verified Keyverse monitoring identity."""

    return AuthorizationContext(
        tenant_record_id=UUID("018f47b2-905a-7b16-bfd4-7e4f53f10e91"),
        role_code="ea_target_state_monitor",
        subject_id="target-state-monitor-123",
        issuer_uri="https://id.example/realms/cwl",
    )


def _status(**changes: object) -> dict[str, object]:
    """Return one database-shaped monitoring decision with optional mutations."""

    status: dict[str, object] = {
        "architecture_transformation_id": _TRANSFORMATION_ID,
        "verification_state_code": "verified",
        "verification_effective_at": "2027-02-02T00:00:00+00:00",
        "verification_recorded_at": "2027-02-02T00:00:01+00:00",
        "evidence_record_id": _EVIDENCE_ID,
        "evidence_age_days": 27,
        "monitoring_state_code": "current",
        "next_action": "continue_monitoring",
    }
    status.update(changes)
    return status


def test_parse_monitoring_request_binds_bitemporal_cutoffs_and_age_policy() -> None:
    """Monitoring accepts only one canonical transformation and bounded age policy."""

    request = parse_target_state_monitoring_request(_PATH)
    assert isinstance(request, TargetStateMonitoringRequest)
    assert str(request.architecture_transformation_id) == _TRANSFORMATION_ID
    assert request.max_evidence_age_days == 90

    with pytest.raises(PlannerRequestError, match="unknown parameters"):
        parse_target_state_monitoring_request(_PATH + "&unsafe=1")
    with pytest.raises(PlannerRequestError, match="between 1 and 3650"):
        parse_target_state_monitoring_request(_PATH.replace("90", "0"))


def test_monitoring_authority_is_separate_and_fail_closed() -> None:
    """General read or verification authority never silently grants monitoring."""

    environment = {
        "EA_OIDC_ISSUER": "https://id.example/realms/cwl",
        "EA_OIDC_AUDIENCE": "enterprise-architecture-core",
        "EA_OIDC_JWKS_URL": (
            "https://id.example/realms/cwl/protocol/openid-connect/certs"
        ),
        "EA_TENANT_CLAIM": "tenant",
        "EA_ROLE_CLAIM": "role",
        "EA_READ_ROLES": "ea_reader",
        "EA_VERIFY_ROLES": "ea_target_state_verifier",
        "EA_MONITOR_ROLES": "ea_target_state_monitor",
    }
    config = build_monitoring_authorization_config(environment)
    assert config is not None
    assert config.allowed_roles == frozenset({"ea_target_state_monitor"})

    environment.pop("EA_MONITOR_ROLES")
    assert build_monitoring_authorization_config(environment) is None


def test_monitoring_reader_returns_actionable_freshness_decision() -> None:
    """The read port binds returned evidence and buyer next action to the request."""

    def runner(command, **kwargs):
        del command, kwargs
        return SimpleNamespace(returncode=0, stdout=json.dumps(_status()), stderr="")

    reader = build_target_state_monitoring_reader(
        "postgresql://ea_runtime@127.0.0.1:5432/ea_core",
        runner=runner,
        base_environment={},
    )
    result = reader(_context(), parse_target_state_monitoring_request(_PATH))
    assert result["monitoring_state_code"] == "current"
    assert result["next_action"] == "continue_monitoring"


def test_monitoring_reader_fails_closed_on_receipt_drift_or_missing_database() -> None:
    """Untrusted or unavailable monitoring evidence never looks actionable."""

    reader = build_target_state_monitoring_reader(None)
    with pytest.raises(PlannerExecutionError, match="unavailable"):
        reader(_context(), parse_target_state_monitoring_request(_PATH))

    def drift_runner(command, **kwargs):
        del command, kwargs
        return SimpleNamespace(
            returncode=0,
            stdout=json.dumps(_status(next_action="done")),
            stderr="",
        )

    reader = build_target_state_monitoring_reader(
        "postgresql://ea_runtime@db.example/ea_core",
        runner=drift_runner,
    )
    with pytest.raises(PlannerExecutionError, match="invalid monitoring status"):
        reader(_context(), parse_target_state_monitoring_request(_PATH))
