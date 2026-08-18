"""Regressions for exact transformation-start contract validation."""

from copy import deepcopy

import pytest

from ea_core_foundation import (
    ContractValidationError,
    validate_asyncapi_document,
    validate_openapi_document,
    validate_openapi_runtime_surface,
)

_START_PATH = (
    "/v1/architecture-transformations/{architecture_transformation_id}/start"
)


def test_start_contract_is_declared_with_distinct_keyverse_authority(
    openapi_document,
) -> None:
    """The executable start command and its purpose role are public contract truth."""

    assert _START_PATH in openapi_document["paths"]
    assert "EA_START_ROLES" in openapi_document["x-keyverse-contract"][
        "requiredConfiguration"
    ]
    validate_openapi_document(openapi_document)
    validate_openapi_runtime_surface(openapi_document)


def test_start_runtime_validation_rejects_operation_or_auth_drift(
    openapi_document,
) -> None:
    """Starting keeps its generated identity and distinct Keyverse authority."""

    changed = deepcopy(openapi_document)
    changed["paths"][_START_PATH]["post"]["operationId"] = "beginTargetState"
    with pytest.raises(ContractValidationError, match="start operationId"):
        validate_openapi_runtime_surface(changed)

    changed = deepcopy(openapi_document)
    changed["paths"][_START_PATH]["post"]["security"] = []
    with pytest.raises(ContractValidationError, match="start must require Keyverse"):
        validate_openapi_runtime_surface(changed)


def test_start_runtime_validation_rejects_parameter_or_body_drift(
    openapi_document,
) -> None:
    """Starting remains aligned with strict command parsing."""

    changed = deepcopy(openapi_document)
    changed["paths"][_START_PATH]["post"]["parameters"] = []
    with pytest.raises(ContractValidationError, match="start parameters"):
        validate_openapi_runtime_surface(changed)

    changed = deepcopy(openapi_document)
    changed["paths"][_START_PATH]["post"]["requestBody"]["required"] = False
    with pytest.raises(ContractValidationError, match="start request body"):
        validate_openapi_runtime_surface(changed)


def test_start_runtime_validation_reuses_parameter_and_response_guards(
    openapi_document,
) -> None:
    """Path UUID and response schemas cannot drift from executable behavior."""

    changed = deepcopy(openapi_document)
    changed["paths"][_START_PATH]["post"]["parameters"][0]["required"] = False
    with pytest.raises(ContractValidationError, match="incorrect required state"):
        validate_openapi_runtime_surface(changed)

    changed = deepcopy(openapi_document)
    changed["paths"][_START_PATH]["post"]["responses"]["201"]["content"][
        "application/json"
    ]["schema"] = {"$ref": "#/components/schemas/ErrorStatus"}
    with pytest.raises(ContractValidationError, match="TargetStateStartReceipt"):
        validate_openapi_runtime_surface(changed)


def test_start_runtime_validation_requires_named_schemas(openapi_document) -> None:
    """Generated clients require both start request and receipt schemas."""

    del openapi_document["components"]["schemas"]["TargetStateStartReceipt"]
    with pytest.raises(ContractValidationError, match="missing OpenAPI schema"):
        validate_openapi_runtime_surface(openapi_document)


def test_start_role_is_required_by_openapi_contract(openapi_document) -> None:
    """Deployments cannot omit the purpose-bound transformation-start role setting."""

    openapi_document["x-keyverse-contract"]["requiredConfiguration"].remove(
        "EA_START_ROLES"
    )
    with pytest.raises(ContractValidationError, match="EA_START_ROLES"):
        validate_openapi_document(openapi_document)


@pytest.mark.parametrize(
    "mutation",
    ["channel", "operation", "message"],
)
def test_start_event_validation_rejects_contract_drift(
    asyncapi_document,
    mutation: str,
) -> None:
    """The started event keeps its address, publisher, and shared envelope."""

    if mutation == "channel":
        asyncapi_document["channels"]["transformationStartEvents"]["address"] = (
            "org.contextualwisdomlab.ea.transformation.start.v1"
        )
        expected = "channel"
    elif mutation == "operation":
        asyncapi_document["operations"]["publishTransformationStarted"]["action"] = (
            "receive"
        )
        expected = "operation"
    else:
        asyncapi_document["components"]["messages"]["TransformationStarted"][
            "payload"
        ] = {"schema": {"type": "object"}}
        expected = "shared Context Graph envelope"
    with pytest.raises(ContractValidationError, match=expected):
        validate_asyncapi_document(asyncapi_document)
