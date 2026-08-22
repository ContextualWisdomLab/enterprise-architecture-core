"""CWL timestamp profile regressions for the planner boundary."""

from __future__ import annotations

import pytest

from ea_core_foundation.service import PlannerRequestError, TargetStatePlanRequest

_TECHNOLOGY_VERSION_ID = "0196f100-1111-7111-8111-111111111111"


def _planner_request(timestamp: str) -> TargetStatePlanRequest:
    """Build one planner request using the same timestamp on both time axes."""

    return TargetStatePlanRequest.from_values(
        _TECHNOLOGY_VERSION_ID,
        timestamp,
        timestamp,
        180,
    )


@pytest.mark.parametrize(
    "valid_timestamp",
    [
        "2027-02-01T00:00:00Z",
        "2027-02-01t00:00:00z",
        "2027-02-01T09:30:00+09:30",
        "2027-02-01T00:00:00.123456Z",
    ],
)
def test_planner_accepts_cwl_timestamp_profile_values(
    valid_timestamp: str,
) -> None:
    """Planner time axes accept the shared leap-second-free CWL profile."""

    request = _planner_request(valid_timestamp)

    assert request.valid_at.tzinfo is not None
    assert request.recorded_at.tzinfo is not None


@pytest.mark.parametrize(
    "invalid_timestamp",
    [
        "20270201T000000Z",
        "2027-W05-1T00:00:00Z",
        "2027-02-01X00:00:00Z",
        "2027-02-01T00:00:00+0000",
        "2027-02-01T00:00:00+00:00:30",
        "2027-02-01T00:00:60Z",
        "2027-02-30T00:00:00Z",
    ],
)
def test_planner_rejects_values_outside_cwl_timestamp_profile(
    invalid_timestamp: str,
) -> None:
    """ISO 8601 forms outside the shared profile cannot reach PostgreSQL."""

    with pytest.raises(PlannerRequestError, match="CWL timestamp profile"):
        _planner_request(invalid_timestamp)
