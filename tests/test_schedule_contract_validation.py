"""Regressions for exact scheduling contract validation."""

from copy import deepcopy

import pytest

from ea_core_foundation import (
    ContractValidationError,
    validate_asyncapi_document,
    validate_openapi_runtime_surface,
)

_SCHEDULE_PATH = (
    "/v1/architecture-transformations/{architecture_transformation_id}/schedule"
)


def test_schedule_runtime_validation_rejects_operation_or_auth_drift(
    openapi_document,
) -> None:
    """Scheduling keeps its generated identity and distinct Keyverse authority."""

    changed = deepcopy(openapi_document)
    changed["paths"][_SCHEDULE_PATH]["post"]["operationId"] = "scheduleTargetState"
    with pytest.raises(ContractValidationError, match="schedule operationId"):
        validate_openapi_runtime_surface(changed)

    changed = deepcopy(openapi_document)
    changed["paths"][_SCHEDULE_PATH]["post"]["security"] = []
    with pytest.raises(ContractValidationError, match="schedule must require Keyverse"):
        validate_openapi_runtime_surface(changed)


def test_schedule_runtime_validation_rejects_parameter_or_body_drift(
    openapi_document,
) -> None:
    """Scheduling remains aligned with strict command parsing."""

    changed = deepcopy(openapi_document)
    changed["paths"][_SCHEDULE_PATH]["post"]["parameters"] = []
    with pytest.raises(ContractValidationError, match="schedule parameters"):
        validate_openapi_runtime_surface(changed)

    changed = deepcopy(openapi_document)
    changed["paths"][_SCHEDULE_PATH]["post"]["requestBody"]["required"] = False
    with pytest.raises(ContractValidationError, match="schedule request body"):
        validate_openapi_runtime_surface(changed)


def test_schedule_runtime_validation_reuses_parameter_and_response_guards(
    openapi_document,
) -> None:
    """Path UUID and response schemas cannot drift from executable behavior."""

    changed = deepcopy(openapi_document)
    changed["paths"][_SCHEDULE_PATH]["post"]["parameters"][0]["required"] = False
    with pytest.raises(ContractValidationError, match="incorrect required state"):
        validate_openapi_runtime_surface(changed)

    changed = deepcopy(openapi_document)
    changed["paths"][_SCHEDULE_PATH]["post"]["responses"]["201"]["content"][
        "application/json"
    ]["schema"] = {"$ref": "#/components/schemas/ErrorStatus"}
    with pytest.raises(ContractValidationError, match="TargetStateScheduleReceipt"):
        validate_openapi_runtime_surface(changed)


def test_schedule_runtime_validation_requires_named_schemas(openapi_document) -> None:
    """Generated clients require both schedule request and receipt schemas."""

    del openapi_document["components"]["schemas"]["TargetStateScheduleReceipt"]
    with pytest.raises(ContractValidationError, match="missing OpenAPI schema"):
        validate_openapi_runtime_surface(openapi_document)


@pytest.mark.parametrize(
    "mutation",
    ["channel", "operation", "message"],
)
def test_schedule_event_validation_rejects_contract_drift(
    asyncapi_document,
    mutation: str,
) -> None:
    """The scheduled event keeps its address, publisher, and shared envelope."""

    if mutation == "channel":
        asyncapi_document["channels"]["transformationScheduleEvents"]["address"] = (
            "org.contextualwisdomlab.ea.transformation.schedule.v1"
        )
        expected = "channel"
    elif mutation == "operation":
        asyncapi_document["operations"]["publishTransformationScheduled"]["action"] = (
            "receive"
        )
        expected = "operation"
    else:
        asyncapi_document["components"]["messages"]["TransformationScheduled"][
            "payload"
        ] = {"schema": {"type": "object"}}
        expected = "shared Context Graph envelope"
    with pytest.raises(ContractValidationError, match=expected):
        validate_asyncapi_document(asyncapi_document)
