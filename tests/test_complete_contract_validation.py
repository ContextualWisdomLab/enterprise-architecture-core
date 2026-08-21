"""Regressions for exact transformation-completion contract validation."""

from copy import deepcopy

import pytest

from ea_core_foundation import (
    ContractValidationError,
    validate_asyncapi_document,
    validate_openapi_document,
    validate_openapi_runtime_surface,
)

_COMPLETE_PATH = (
    "/v1/architecture-transformations/{architecture_transformation_id}/complete"
)


def test_complete_contract_is_declared_with_distinct_keyverse_authority(
    openapi_document,
) -> None:
    """The executable completion command and purpose role are public truth."""

    assert _COMPLETE_PATH in openapi_document["paths"]
    assert "EA_COMPLETE_ROLES" in openapi_document["x-keyverse-contract"][
        "requiredConfiguration"
    ]
    validate_openapi_document(openapi_document)
    validate_openapi_runtime_surface(openapi_document)


def test_complete_runtime_validation_rejects_operation_or_auth_drift(
    openapi_document,
) -> None:
    """Completion keeps its generated identity and distinct Keyverse authority."""

    changed = deepcopy(openapi_document)
    changed["paths"][_COMPLETE_PATH]["post"]["operationId"] = "finishTargetState"
    with pytest.raises(ContractValidationError, match="complete operationId"):
        validate_openapi_runtime_surface(changed)

    changed = deepcopy(openapi_document)
    changed["paths"][_COMPLETE_PATH]["post"]["security"] = []
    with pytest.raises(ContractValidationError, match="complete must require Keyverse"):
        validate_openapi_runtime_surface(changed)


def test_complete_runtime_validation_rejects_parameter_or_body_drift(
    openapi_document,
) -> None:
    """Completion stays aligned with strict command parsing."""

    changed = deepcopy(openapi_document)
    changed["paths"][_COMPLETE_PATH]["post"]["parameters"] = []
    with pytest.raises(ContractValidationError, match="complete parameters"):
        validate_openapi_runtime_surface(changed)

    changed = deepcopy(openapi_document)
    changed["paths"][_COMPLETE_PATH]["post"]["requestBody"]["required"] = False
    with pytest.raises(ContractValidationError, match="complete request body"):
        validate_openapi_runtime_surface(changed)


def test_complete_runtime_validation_reuses_parameter_and_response_guards(
    openapi_document,
) -> None:
    """Path UUID and response schemas cannot drift from executable behavior."""

    changed = deepcopy(openapi_document)
    changed["paths"][_COMPLETE_PATH]["post"]["parameters"][0]["required"] = False
    with pytest.raises(ContractValidationError, match="incorrect required state"):
        validate_openapi_runtime_surface(changed)

    changed = deepcopy(openapi_document)
    changed["paths"][_COMPLETE_PATH]["post"]["responses"]["201"]["content"][
        "application/json"
    ]["schema"] = {"$ref": "#/components/schemas/ErrorStatus"}
    with pytest.raises(ContractValidationError, match="TargetStateCompleteReceipt"):
        validate_openapi_runtime_surface(changed)


def test_complete_runtime_validation_requires_named_schemas(openapi_document) -> None:
    """Generated clients require both completion request and receipt schemas."""

    del openapi_document["components"]["schemas"]["TargetStateCompleteReceipt"]
    with pytest.raises(ContractValidationError, match="missing OpenAPI schema"):
        validate_openapi_runtime_surface(openapi_document)


def test_complete_role_is_required_by_openapi_contract(openapi_document) -> None:
    """Deployments cannot omit the purpose-bound completion role setting."""

    openapi_document["x-keyverse-contract"]["requiredConfiguration"].remove(
        "EA_COMPLETE_ROLES"
    )
    with pytest.raises(ContractValidationError, match="EA_COMPLETE_ROLES"):
        validate_openapi_document(openapi_document)


@pytest.mark.parametrize("mutation", ["channel", "operation", "message"])
def test_complete_event_validation_rejects_contract_drift(
    asyncapi_document,
    mutation: str,
) -> None:
    """The completed event keeps its address, publisher, and shared envelope."""

    if mutation == "channel":
        asyncapi_document["channels"]["transformationCompleteEvents"]["address"] = (
            "org.contextualwisdomlab.ea.transformation.complete.v1"
        )
        expected = "channel"
    elif mutation == "operation":
        asyncapi_document["operations"]["publishTransformationCompleted"][
            "action"
        ] = "receive"
        expected = "operation"
    else:
        asyncapi_document["components"]["messages"]["TransformationCompleted"][
            "payload"
        ] = {"schema": {"type": "object"}}
        expected = "shared Context Graph envelope"
    with pytest.raises(ContractValidationError, match=expected):
        validate_asyncapi_document(asyncapi_document)
