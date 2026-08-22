"""Regressions keeping generated planner clients aligned with runtime identity/time parsing."""

from __future__ import annotations

from copy import deepcopy

import pytest
from jsonschema import ValidationError, validate

from ea_core_foundation import ContractValidationError, validate_openapi_runtime_surface

_PLANNER_PATH = "/v1/technology-target-state-plans/{technology_version_id}"


def _planner_parameters(openapi_document: dict) -> list[dict]:
    """Return the checked-in planner parameter array."""

    return openapi_document["paths"][_PLANNER_PATH]["get"]["parameters"]


def test_planner_uuid_schema_rejects_non_uuidv7(openapi_document) -> None:
    """Generated clients cannot send a UUIDv4 value that runtime rejects."""

    schema = _planner_parameters(openapi_document)[0]["schema"]
    validate("0196f100-1111-7111-8111-111111111111", schema)
    with pytest.raises(ValidationError):
        validate("550e8400-e29b-41d4-a716-446655440000", schema)


def test_planner_time_schema_rejects_leap_seconds(openapi_document) -> None:
    """Generated clients cannot send leap seconds outside the CWL profile."""

    for parameter in _planner_parameters(openapi_document)[1:3]:
        schema = parameter["schema"]
        validate("2027-02-01T00:00:00Z", schema)
        with pytest.raises(ValidationError):
            validate("2027-02-01T00:00:60Z", schema)


def test_repository_validation_rejects_wire_profile_drift(openapi_document) -> None:
    """Removing the exact UUIDv7 regex must fail deterministic contract validation."""

    changed = deepcopy(openapi_document)
    del _planner_parameters(changed)[0]["schema"]["pattern"]

    with pytest.raises(ContractValidationError, match="planner wire profile"):
        validate_openapi_runtime_surface(changed)
