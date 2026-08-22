"""OpenAPI foundation validation tests."""

from copy import deepcopy

import pytest

from ea_core_foundation import ContractValidationError, validate_openapi_document


def test_checked_in_openapi_contract_is_valid(openapi_document) -> None:
    """The checked-in OpenAPI document exposes only implemented operations."""

    assert validate_openapi_document(openapi_document) == 5


def test_openapi_rejects_wrong_version(openapi_document) -> None:
    """The contract uses one explicit OpenAPI dialect."""

    openapi_document["openapi"] = "3.1.1"
    with pytest.raises(ContractValidationError, match="3.2.0"):
        validate_openapi_document(openapi_document)


@pytest.mark.parametrize("paths_value", [None, []])
def test_openapi_requires_paths_object(openapi_document, paths_value) -> None:
    """Paths must be represented as a JSON object."""

    openapi_document["paths"] = paths_value
    with pytest.raises(ContractValidationError, match="paths must be an object"):
        validate_openapi_document(openapi_document)


def test_openapi_rejects_path_without_leading_slash(openapi_document) -> None:
    """Path keys use RFC-style absolute API paths."""

    openapi_document["paths"] = {"health": {"get": {"operationId": "getHealth"}}}
    with pytest.raises(ContractValidationError, match="start with /"):
        validate_openapi_document(openapi_document)


def test_openapi_rejects_non_object_path_item(openapi_document) -> None:
    """Each path item must be an object."""

    openapi_document["paths"] = {"/health": []}
    with pytest.raises(ContractValidationError, match="path /health"):
        validate_openapi_document(openapi_document)


def test_openapi_ignores_non_operation_path_fields(openapi_document) -> None:
    """Path-level metadata does not count as an operation."""

    openapi_document["paths"] = {
        "/health": {
            "parameters": [],
            "get": {"operationId": "getHealth"},
        }
    }
    assert validate_openapi_document(openapi_document) == 1


def test_openapi_rejects_non_object_operation(openapi_document) -> None:
    """HTTP method values must be operation objects."""

    openapi_document["paths"] = {"/health": {"get": []}}
    with pytest.raises(ContractValidationError, match="operation must be an object"):
        validate_openapi_document(openapi_document)


@pytest.mark.parametrize("operation_id", [None, ""])
def test_openapi_requires_operation_id(openapi_document, operation_id) -> None:
    """Every operation has a stable generated-client identity."""

    openapi_document["paths"] = {
        "/health": {"get": {"operationId": operation_id}}
    }
    with pytest.raises(ContractValidationError, match="requires operationId"):
        validate_openapi_document(openapi_document)


def test_openapi_rejects_duplicate_operation_id(openapi_document) -> None:
    """Generated clients cannot contain colliding operation names."""

    openapi_document["paths"] = {
        "/health": {"get": {"operationId": "sameOperation"}},
        "/ready": {"get": {"operationId": "sameOperation"}},
    }
    with pytest.raises(ContractValidationError, match="duplicate operationId"):
        validate_openapi_document(openapi_document)


def test_openapi_requires_at_least_one_operation(openapi_document) -> None:
    """A document containing only path metadata is not a service contract."""

    openapi_document["paths"] = {"/health": {"parameters": []}}
    with pytest.raises(ContractValidationError, match="must define operations"):
        validate_openapi_document(openapi_document)


def test_openapi_requires_components_object(openapi_document) -> None:
    """Components must be a JSON object before security is inspected."""

    openapi_document["components"] = []
    with pytest.raises(ContractValidationError, match="components must be an object"):
        validate_openapi_document(openapi_document)


def test_openapi_requires_security_schemes_object(openapi_document) -> None:
    """Security schemes must be represented as a JSON object."""

    openapi_document["components"] = {"securitySchemes": []}
    with pytest.raises(
        ContractValidationError, match="securitySchemes must be an object"
    ):
        validate_openapi_document(openapi_document)


def test_openapi_requires_keyverse_security_scheme(openapi_document) -> None:
    """The initial service is not allowed to invent a local identity provider."""

    openapi_document["components"]["securitySchemes"] = {}
    with pytest.raises(ContractValidationError, match="Keyverse bearer"):
        validate_openapi_document(openapi_document)


def test_openapi_requires_keyverse_contract_object(openapi_document) -> None:
    """OIDC verification requirements are a structured extension."""

    openapi_document["x-keyverse-contract"] = []
    with pytest.raises(ContractValidationError, match="x-keyverse-contract"):
        validate_openapi_document(openapi_document)


def test_openapi_rejects_incomplete_keyverse_checks(openapi_document) -> None:
    """Signature-only JWT checking is not an acceptable authentication gate."""

    changed = deepcopy(openapi_document)
    changed["x-keyverse-contract"]["requiredChecks"] = ["signature"]
    with pytest.raises(ContractValidationError, match="checks are incomplete"):
        validate_openapi_document(changed)


def test_openapi_rejects_incomplete_keyverse_runtime_configuration(
    openapi_document,
) -> None:
    """The contract must name every fail-closed runtime authorization setting."""

    changed = deepcopy(openapi_document)
    changed["x-keyverse-contract"]["requiredConfiguration"] = [
        "EA_OIDC_ISSUER",
        "EA_OIDC_AUDIENCE",
    ]
    with pytest.raises(ContractValidationError, match="configuration is incomplete"):
        validate_openapi_document(changed)
