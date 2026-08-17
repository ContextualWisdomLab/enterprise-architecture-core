"""Canonical UUIDv7 regression tests for the planner boundary."""

from __future__ import annotations

import pytest

from ea_core_foundation.service import PlannerRequestError, TargetStatePlanRequest

_CANONICAL_TECHNOLOGY_VERSION_ID = "0196f100-1111-7111-8111-111111111111"


def _planner_request(technology_version_id: str) -> TargetStatePlanRequest:
    """Build one otherwise-valid bitemporal planner request."""

    return TargetStatePlanRequest.from_values(
        technology_version_id,
        "2027-02-01T00:00:00Z",
        "2027-02-01T00:00:00Z",
        180,
    )


def test_planner_accepts_canonical_uuidv7_technology_identity() -> None:
    """The wire identity accepted by the planner matches the EA UUIDv7 contract."""

    request = _planner_request(_CANONICAL_TECHNOLOGY_VERSION_ID)

    assert str(request.technology_version_id) == _CANONICAL_TECHNOLOGY_VERSION_ID


@pytest.mark.parametrize(
    "invalid_identity",
    [
        "550e8400-e29b-41d4-a716-446655440000",
        _CANONICAL_TECHNOLOGY_VERSION_ID.upper(),
        _CANONICAL_TECHNOLOGY_VERSION_ID.replace("-", ""),
        "{" + _CANONICAL_TECHNOLOGY_VERSION_ID + "}",
    ],
)
def test_planner_rejects_noncanonical_or_non_uuidv7_technology_identity(
    invalid_identity: str,
) -> None:
    """A syntactically valid non-v7 or alternate spelling cannot yield an empty plan."""

    with pytest.raises(PlannerRequestError, match="canonical UUIDv7"):
        _planner_request(invalid_identity)
