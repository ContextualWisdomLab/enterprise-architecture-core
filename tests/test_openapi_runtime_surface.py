"""Regressions for the implemented OpenAPI process and planner surface."""

from copy import deepcopy

import pytest
from jsonschema import ValidationError, validate

from ea_core_foundation import (
    ContractValidationError,
    validate_openapi_runtime_surface,
)

_PLANNER_PATH = "/v1/technology-target-state-plans/{technology_version_id}"


def test_checked_in_openapi_runtime_surface_is_truthful(openapi_document) -> None:
    """The advertised process and planner surface matches implemented HTTP routes."""

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


@pytest.mark.parametrize(
    "schema_name",
    [
        "HealthStatus",
        "ReadyStatus",
        "TargetStatePlanResponse",
        "TargetStateDecision",
        "ErrorStatus",
    ],
)
def test_runtime_surface_requires_named_component_schemas(
    openapi_document, schema_name: str
) -> None:
    """Every executable response shape remains named for generated clients."""

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
    """Named response schemas live under components.schemas."""

    openapi_document["components"]["schemas"] = []
    with pytest.raises(ContractValidationError, match="schemas must be an object"):
        validate_openapi_runtime_surface(openapi_document)


def test_planner_requires_exact_operation_identity_and_keyverse_security(
    openapi_document,
) -> None:
    """The planner cannot silently become anonymous or change generated identity."""

    changed = deepcopy(openapi_document)
    changed["paths"][_PLANNER_PATH]["get"]["operationId"] = "getTechnologyPlan"
    with pytest.raises(ContractValidationError, match="planner operationId"):
        validate_openapi_runtime_surface(changed)

    changed = deepcopy(openapi_document)
    changed["paths"][_PLANNER_PATH]["get"]["security"] = []
    with pytest.raises(ContractValidationError, match="Keyverse bearer"):
        validate_openapi_runtime_surface(changed)


def test_planner_requires_exact_unique_parameter_set(openapi_document) -> None:
    """OpenAPI parameters stay byte-for-behavior aligned with request parsing."""

    changed = deepcopy(openapi_document)
    changed["paths"][_PLANNER_PATH]["get"]["parameters"] = {}
    with pytest.raises(ContractValidationError, match="parameters must be an array"):
        validate_openapi_runtime_surface(changed)

    changed = deepcopy(openapi_document)
    parameters = changed["paths"][_PLANNER_PATH]["get"]["parameters"]
    parameters.append(deepcopy(parameters[0]))
    with pytest.raises(ContractValidationError, match="duplicate planner parameter"):
        validate_openapi_runtime_surface(changed)

    changed = deepcopy(openapi_document)
    del changed["paths"][_PLANNER_PATH]["get"]["parameters"][-1]
    with pytest.raises(ContractValidationError, match="match executable request"):
        validate_openapi_runtime_surface(changed)

    changed = deepcopy(openapi_document)
    changed["paths"][_PLANNER_PATH]["get"]["parameters"][0]["name"] = 7
    with pytest.raises(ContractValidationError, match="identity is incomplete"):
        validate_openapi_runtime_surface(changed)


def test_planner_requires_exact_parameter_required_state_and_schema(
    openapi_document,
) -> None:
    """UUID/time/horizon semantics cannot drift from the executable parser."""

    changed = deepcopy(openapi_document)
    changed["paths"][_PLANNER_PATH]["get"]["parameters"][0]["required"] = False
    with pytest.raises(ContractValidationError, match="incorrect required state"):
        validate_openapi_runtime_surface(changed)

    changed = deepcopy(openapi_document)
    changed["paths"][_PLANNER_PATH]["get"]["parameters"][1]["schema"] = {
        "type": "string"
    }
    with pytest.raises(ContractValidationError, match="incorrect schema"):
        validate_openapi_runtime_surface(changed)

    changed = deepcopy(openapi_document)
    changed["paths"][_PLANNER_PATH]["get"]["parameters"][0]["schema"][
        "pattern"
    ] = "^[0-9a-f-]+$"
    with pytest.raises(ContractValidationError, match="incorrect schema"):
        validate_openapi_runtime_surface(changed)


def test_planner_uuid_schema_matches_uuidv7_runtime_boundary(openapi_document) -> None:
    """Generated clients cannot send UUIDv4 values the runtime rejects."""

    schema = openapi_document["paths"][_PLANNER_PATH]["get"]["parameters"][0][
        "schema"
    ]
    validate(
        "0196f100-1111-7111-8111-111111111111",
        schema,
    )
    with pytest.raises(ValidationError):
        validate("550e8400-e29b-41d4-a716-446655440000", schema)


def test_planner_timestamp_schema_matches_cwl_runtime_boundary(
    openapi_document,
) -> None:
    """Generated clients cannot send leap seconds the runtime rejects."""

    parameters = openapi_document["paths"][_PLANNER_PATH]["get"]["parameters"]
    for parameter in parameters[1:3]:
        schema = parameter["schema"]
        validate("2027-02-01T00:00:00Z", schema)
        with pytest.raises(ValidationError):
            validate("2027-02-01T00:00:60Z", schema)


def test_planner_requires_success_and_error_response_shapes(openapi_document) -> None:
    """Buyer decisions and fail-closed errors keep stable generated shapes."""

    changed = deepcopy(openapi_document)
    changed["paths"][_PLANNER_PATH]["get"]["responses"]["200"]["content"][
        "application/json"
    ]["schema"] = {"$ref": "#/components/schemas/ErrorStatus"}
    with pytest.raises(ContractValidationError, match="TargetStatePlanResponse"):
        validate_openapi_runtime_surface(changed)

    changed = deepcopy(openapi_document)
    changed["paths"][_PLANNER_PATH]["get"]["responses"]["401"]["content"][
        "application/json"
    ]["schema"] = {"$ref": "#/components/schemas/ReadyStatus"}
    with pytest.raises(ContractValidationError, match="ErrorStatus"):
        validate_openapi_runtime_surface(changed)
