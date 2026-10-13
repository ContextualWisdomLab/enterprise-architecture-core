"""Regression coverage for explicit truth on reassessment status decisions."""

from __future__ import annotations

import json
from types import SimpleNamespace
from uuid import UUID

from ea_core_foundation.authorization import AuthorizationContext
from ea_core_foundation.data_management_recheck_status import (
    build_data_management_recheck_status_reader,
    parse_data_management_recheck_status_request,
)

_RECHECK_ID = "0196f300-1111-7111-8111-111111111174"
_ASSESSMENT_ID = "0196f300-1111-7111-8111-111111111171"
_SUCCESSOR_ID = "0196f300-1111-7111-8111-111111111181"
_PATH = f"/v1/data-management-assessment-rechecks/{_RECHECK_ID}"


def _context() -> AuthorizationContext:
    """Return one already-verified tenant-scoped reassessment-status reader."""

    return AuthorizationContext(
        tenant_record_id=UUID("018f47b2-905a-7b16-bfd4-7e4f53f10e91"),
        role_code="ea_data_management_recheck_reader",
        subject_id="data-governance-lead-123",
        issuer_uri="https://id.example/realms/cwl",
    )


def test_proposed_successor_requires_review_instead_of_closing_loop() -> None:
    """A proposed successor remains visible but cannot become decision-complete."""

    payload = {
        "assessment_recheck_request_id": _RECHECK_ID,
        "data_management_assessment_projection_id": _ASSESSMENT_ID,
        "successor_assessment_projection_id": _SUCCESSOR_ID,
        "successor_truth_status_code": "proposed",
        "recheck_state_code": "review_required",
        "successor_readiness_code": "evidence_complete",
        "successor_overall_score_basis_points": 10000,
        "successor_missing_evidence_count": 0,
        "next_action": "review_assessment_recheck_evidence",
    }

    def runner(command, **kwargs):
        del command, kwargs
        return SimpleNamespace(
            returncode=0,
            stdout=json.dumps(payload),
            stderr="",
        )

    reader = build_data_management_recheck_status_reader(
        "postgresql://ea_runtime@db.example/ea_core",
        runner=runner,
    )
    result = reader(_context(), parse_data_management_recheck_status_request(_PATH))

    assert result["successor_truth_status_code"] == "proposed"
    assert result["recheck_state_code"] == "review_required"
    assert result["next_action"] == "review_assessment_recheck_evidence"
