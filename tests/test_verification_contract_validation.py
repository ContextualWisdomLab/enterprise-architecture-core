"""Regressions for exact target-state verification contract validation."""

from copy import deepcopy

import pytest

from ea_core_foundation import (
    ContractValidationError,
    validate_asyncapi_document,
    validate_openapi_document,
    validate_openapi_runtime_surface,
)

_VERIFY_PATH = (
    "/v1/architecture-transformations/{architecture_transformation_id}/verification"
)


def test_verification_contract_is_declared_with_distinct_keyverse_authority(
    openapi_document,
) -> None:
    """The executable verification decision and purpose role are public truth."""

    assert _VERIFY_PATH in openapi_document["paths"]
    assert "EA_VERIFY_ROLES" in openapi_document["x-keyverse-contract"][
        "requiredConfiguration"
    ]
    validate_openapi_document(openapi_document)
    validate_openapi_runtime_surface(openapi_document)


def test_verification_runtime_validation_rejects_operation_or_auth_drift(
    openapi_document,
) -> None:
    """Verification keeps its generated identity and distinct Keyverse authority."""

    changed = deepcopy(openapi_document)
    changed["paths"][_VERIFY_PATH]["post"]["operationId"] = "autoVerifyTargetState"
    with pytest.raises(ContractValidationError, match="verification operationId"):
        validate_openapi_runtime_surface(changed)

    changed = deepcopy(openapi_document)
    changed["paths"][_VERIFY_PATH]["post"]["security"] = []
    with pytest.raises(
        ContractValidationError,
        match="verification must require Keyverse",
    ):
        validate_openapi_runtime_surface(changed)


def test_verification_runtime_validation_rejects_body_or_schema_drift(
    openapi_document,
) -> None:
    """Verification stays aligned with strict command parsing and receipts."""

    changed = deepcopy(openapi_document)
    changed["paths"][_VERIFY_PATH]["post"]["requestBody"]["required"] = False
    with pytest.raises(ContractValidationError, match="verification request body"):
        validate_openapi_runtime_surface(changed)

    changed = deepcopy(openapi_document)
    changed["paths"][_VERIFY_PATH]["post"]["responses"]["201"]["content"][
        "application/json"
    ]["schema"] = {"$ref": "#/components/schemas/ErrorStatus"}
    with pytest.raises(ContractValidationError, match="TargetStateVerificationReceipt"):
        validate_openapi_runtime_surface(changed)

    del changed["components"]["schemas"]["TargetStateVerificationReceipt"]
    with pytest.raises(ContractValidationError):
        validate_openapi_runtime_surface(changed)


def test_verification_role_is_required_by_openapi_contract(openapi_document) -> None:
    """Deployments cannot omit the purpose-bound verification role setting."""

    openapi_document["x-keyverse-contract"]["requiredConfiguration"].remove(
        "EA_VERIFY_ROLES"
    )
    with pytest.raises(ContractValidationError, match="EA_VERIFY_ROLES"):
        validate_openapi_document(openapi_document)


@pytest.mark.parametrize("mutation", ["channel", "operation", "message"])
def test_verification_event_validation_rejects_contract_drift(
    asyncapi_document,
    mutation: str,
) -> None:
    """Verification events keep address, publisher, and shared envelope semantics."""

    if mutation == "channel":
        asyncapi_document["channels"]["transformationVerificationEvents"][
            "address"
        ] = "org.contextualwisdomlab.ea.transformation.auto_verified.v1"
        expected = "channel"
    elif mutation == "operation":
        asyncapi_document["operations"]["publishTransformationVerificationRecorded"][
            "action"
        ] = "receive"
        expected = "operation"
    else:
        asyncapi_document["components"]["messages"][
            "TransformationVerificationRecorded"
        ]["payload"] = {"schema": {"type": "object"}}
        expected = "shared Context Graph envelope"
    with pytest.raises(ContractValidationError, match=expected):
        validate_asyncapi_document(asyncapi_document)
