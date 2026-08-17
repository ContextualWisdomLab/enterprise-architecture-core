"""Regressions for the implemented OpenAPI health and ready surface."""

from copy import deepcopy

import pytest

from ea_core_foundation import (
    ContractValidationError,
    validate_openapi_runtime_surface,
)


def test_checked_in_openapi_runtime_surface_is_truthful(openapi_document) -> None:
    """The advertised process surface matches the implemented HTTP routes."""

    validate_openapi_runtime_surface(openapi_document)


def test_runtime_surface_rejects_undeclared_or_missing_paths(openapi_document) -> None:
    """Placeholder CRUD paths cannot return to the implemented contract."""

    openapi_document["paths"]["/capabilities"] = {
        "post": {"operationId": "createCapability"}
    }
    with pytest.raises(ContractValidationError, match="only implemented"):
        validate_openapi_runtime_surface(openapi_document)


def test_runtime_surface_requires_documented_operation_identity(
    openapi_document,
) -> None:
    """Generated clients keep stable operation names for health and ready."""

    openapi_document["paths"]["/health"]["get"]["operationId"] = "ping"
    with pytest.raises(ContractValidationError, match="operationId must be getHealth"):
        validate_openapi_runtime_surface(openapi_document)


def test_runtime_surface_stays_unauthenticated(openapi_document) -> None:
    """Liveness and readiness remain callable before a Keyverse token exists."""

    openapi_document["paths"]["/ready"]["get"]["security"] = [{"keyverseBearer": []}]
    with pytest.raises(ContractValidationError, match="must remain unauthenticated"):
        validate_openapi_runtime_surface(openapi_document)


def test_runtime_surface_requires_json_response_schemas(openapi_document) -> None:
    """Deleting a response schema makes the probe unusable to generated clients."""

    changed = deepcopy(openapi_document)
    del changed["paths"]["/health"]["get"]["responses"]["200"]["content"]
    with pytest.raises(ContractValidationError, match="/health 200 content"):
        validate_openapi_runtime_surface(changed)

    changed = deepcopy(openapi_document)
    changed["paths"]["/ready"]["get"]["responses"]["503"]["content"][
        "application/json"
    ]["schema"] = {"$ref": "#/components/schemas/HealthStatus"}
    with pytest.raises(ContractValidationError, match="must reference ReadyStatus"):
        validate_openapi_runtime_surface(changed)


@pytest.mark.parametrize("schema_name", ["HealthStatus", "ReadyStatus"])
def test_runtime_surface_requires_named_component_schemas(
    openapi_document, schema_name: str
) -> None:
    """Health and ready payloads stay named so clients do not invent shapes."""

    del openapi_document["components"]["schemas"][schema_name]
    with pytest.raises(ContractValidationError, match="missing OpenAPI schema"):
        validate_openapi_runtime_surface(openapi_document)


def test_runtime_surface_requires_paths_object() -> None:
    """A non-object paths value fails before route comparison."""

    with pytest.raises(ContractValidationError, match="paths must be an object"):
        validate_openapi_runtime_surface({"paths": []})


def test_runtime_surface_requires_get_operation_objects(openapi_document) -> None:
    """Each implemented path must expose a GET operation object."""

    openapi_document["paths"]["/health"] = []
    with pytest.raises(ContractValidationError, match="path /health"):
        validate_openapi_runtime_surface(openapi_document)


def test_runtime_surface_requires_get_mapping(openapi_document) -> None:
    """A missing GET operation cannot be treated as implemented."""

    openapi_document["paths"]["/ready"]["get"] = []
    with pytest.raises(ContractValidationError, match="/ready get"):
        validate_openapi_runtime_surface(openapi_document)


def test_runtime_surface_requires_response_and_json_objects(openapi_document) -> None:
    """Response metadata is not a substitute for a JSON schema."""

    openapi_document["paths"]["/health"]["get"]["responses"] = []
    with pytest.raises(ContractValidationError, match="/health responses"):
        validate_openapi_runtime_surface(openapi_document)

    openapi_document = {
        **openapi_document,
        "paths": {
            **openapi_document["paths"],
            "/health": {
                "get": {
                    "operationId": "getHealth",
                    "security": [],
                    "responses": {"200": []},
                }
            },
        },
    }
    with pytest.raises(ContractValidationError, match="/health 200"):
        validate_openapi_runtime_surface(openapi_document)


def test_runtime_surface_requires_application_json_schema_object(
    openapi_document,
) -> None:
    """A content map without application/json is not a usable probe contract."""

    openapi_document["paths"]["/health"]["get"]["responses"]["200"]["content"] = {
        "text/plain": {}
    }
    with pytest.raises(ContractValidationError, match="application/json"):
        validate_openapi_runtime_surface(openapi_document)

    openapi_document["paths"]["/health"]["get"]["responses"]["200"]["content"] = {
        "application/json": []
    }
    with pytest.raises(ContractValidationError, match="application/json"):
        validate_openapi_runtime_surface(openapi_document)

    openapi_document["paths"]["/health"]["get"]["responses"]["200"]["content"] = {
        "application/json": {"schema": []}
    }
    with pytest.raises(ContractValidationError, match="/health 200 schema"):
        validate_openapi_runtime_surface(openapi_document)


def test_runtime_surface_requires_schema_components_object(openapi_document) -> None:
    """Named health and ready schemas live under components.schemas."""

    openapi_document["components"]["schemas"] = []
    with pytest.raises(ContractValidationError, match="schemas must be an object"):
        validate_openapi_runtime_surface(openapi_document)
