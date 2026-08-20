"""Fail-closed contract validation for data-management reassessment status reads."""

from copy import deepcopy

import pytest

import ea_core_foundation.validation_data_management_recheck_status as status_validation

_STATUS_PATH = (
    "/v1/data-management-assessment-rechecks/"
    "{assessment_recheck_request_id}"
)


def test_status_layer_accepts_current_openapi_contract(openapi_document) -> None:
    """The newest validator recognizes all twelve implemented API operations."""

    assert status_validation.validate_openapi_document(openapi_document) == 12
    status_validation.validate_openapi_runtime_surface(openapi_document)


def test_status_layer_requires_distinct_read_authority(openapi_document) -> None:
    """Status reads cannot silently inherit the reassessment command authority."""

    changed = deepcopy(openapi_document)
    changed["x-keyverse-contract"]["requiredConfiguration"].remove(
        "EA_DATA_MANAGEMENT_RECHECK_READ_ROLES"
    )

    with pytest.raises(
        status_validation.ContractValidationError,
        match="must include EA_DATA_MANAGEMENT_RECHECK_READ_ROLES",
    ):
        status_validation.validate_openapi_document(changed)


def test_status_layer_rejects_route_identity_drift(openapi_document) -> None:
    """Generated clients keep one exact reassessment-status operation identity."""

    changed = deepcopy(openapi_document)
    changed["paths"][_STATUS_PATH]["get"]["operationId"] = "getSomeOtherStatus"

    with pytest.raises(
        status_validation.ContractValidationError,
        match="operationId must be getDataManagementAssessmentRecheckStatus",
    ):
        status_validation.validate_openapi_runtime_surface(changed)


def test_status_layer_requires_exact_uuid7_path_parameter(openapi_document) -> None:
    """The published request identifier remains aligned with executable parsing."""

    changed = deepcopy(openapi_document)
    changed["paths"][_STATUS_PATH]["get"]["parameters"] = []

    with pytest.raises(
        status_validation.ContractValidationError,
        match="parameters must match executable parsing",
    ):
        status_validation.validate_openapi_runtime_surface(changed)


def test_status_layer_requires_response_schema(openapi_document) -> None:
    """A status route without its named response contract must fail closed."""

    changed = deepcopy(openapi_document)
    changed["components"]["schemas"].pop("DataManagementAssessmentRecheckStatus")

    with pytest.raises(
        status_validation.ContractValidationError,
        match="missing OpenAPI schema",
    ):
        status_validation.validate_openapi_runtime_surface(changed)
