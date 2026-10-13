"""Mutation regressions for the target-state monitoring OpenAPI boundary."""

from copy import deepcopy

import pytest

from ea_core_foundation import ContractValidationError, validate_openapi_runtime_surface

_MONITORING_PATH = (
    "/v1/architecture-transformations/{architecture_transformation_id}/monitoring"
)


def test_monitoring_contract_rejects_operation_identity_drift(openapi_document) -> None:
    """Generated clients cannot silently bind monitoring to another operation."""

    changed = deepcopy(openapi_document)
    changed["paths"][_MONITORING_PATH]["get"]["operationId"] = "monitorTargetState"
    with pytest.raises(ContractValidationError, match="monitoring operationId"):
        validate_openapi_runtime_surface(changed)


def test_monitoring_contract_rejects_authorization_drift(openapi_document) -> None:
    """The monitoring read cannot become anonymous or inherit another authority."""

    changed = deepcopy(openapi_document)
    changed["paths"][_MONITORING_PATH]["get"]["security"] = []
    with pytest.raises(ContractValidationError, match="Keyverse bearer"):
        validate_openapi_runtime_surface(changed)


def test_monitoring_contract_rejects_parameter_set_drift(openapi_document) -> None:
    """The published monitoring parameters stay aligned with executable parsing."""

    changed = deepcopy(openapi_document)
    del changed["paths"][_MONITORING_PATH]["get"]["parameters"][-1]
    with pytest.raises(ContractValidationError, match="parameters must match"):
        validate_openapi_runtime_surface(changed)
