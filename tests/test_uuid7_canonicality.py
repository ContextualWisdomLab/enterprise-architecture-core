"""Canonical UUIDv7 regressions for the EA approval boundary."""

from __future__ import annotations

import pytest

from ea_core_foundation.service import (
    PlannerRequestError,
    TargetStateApprovalRequest,
    parse_target_state_approval_request,
)

_TRANSFORMATION_ID = "0196e010-1111-7111-8111-111111111191"
_DECISION_REQUEST_ID = "0196e030-1111-7111-8111-111111111191"
_EVIDENCE_ID = "0195d145-64e8-7f4f-8a23-a0cc784cbf10"


def _approval_payload(
    *,
    decision_request_id: str = _DECISION_REQUEST_ID,
    evidence_record_id: str = _EVIDENCE_ID,
) -> dict[str, object]:
    """Return one otherwise-valid target-state approval command payload."""

    return {
        "decision_request_id": decision_request_id,
        "effective_at": "2027-01-15T00:00:00Z",
        "decision_reason_text": "Architecture board approved reviewed evidence.",
        "evidence_record_id": evidence_record_id,
    }


@pytest.mark.parametrize(
    "noncanonical_id",
    [
        _TRANSFORMATION_ID.upper(),
        _TRANSFORMATION_ID.replace("-", ""),
        "{" + _TRANSFORMATION_ID + "}",
    ],
)
def test_approval_path_rejects_noncanonical_uuidv7_text(
    noncanonical_id: str,
) -> None:
    """Equivalent spellings cannot bypass canonical command identity."""

    with pytest.raises(PlannerRequestError, match="canonical UUIDv7"):
        parse_target_state_approval_request(
            f"/v1/architecture-transformations/{noncanonical_id}/approval",
            _approval_payload(),
        )


@pytest.mark.parametrize(
    "noncanonical_id",
    [
        _DECISION_REQUEST_ID.upper(),
        _DECISION_REQUEST_ID.replace("-", ""),
        "{" + _DECISION_REQUEST_ID + "}",
    ],
)
def test_decision_request_rejects_noncanonical_uuidv7_text(
    noncanonical_id: str,
) -> None:
    """Idempotency keys use one portable text identity before PostgreSQL."""

    with pytest.raises(PlannerRequestError, match="canonical UUIDv7"):
        TargetStateApprovalRequest.from_values(
            _TRANSFORMATION_ID,
            noncanonical_id,
            "2027-01-15T00:00:00Z",
            "Architecture board approved reviewed evidence.",
            _EVIDENCE_ID,
        )


@pytest.mark.parametrize(
    "noncanonical_id",
    [
        _EVIDENCE_ID.upper(),
        _EVIDENCE_ID.replace("-", ""),
        "{" + _EVIDENCE_ID + "}",
    ],
)
def test_evidence_reference_rejects_noncanonical_uuidv7_text(
    noncanonical_id: str,
) -> None:
    """Approval evidence cannot have multiple accepted wire spellings."""

    with pytest.raises(PlannerRequestError, match="canonical UUIDv7"):
        TargetStateApprovalRequest.from_values(
            _TRANSFORMATION_ID,
            _DECISION_REQUEST_ID,
            "2027-01-15T00:00:00Z",
            "Architecture board approved reviewed evidence.",
            noncanonical_id,
        )
