"""Data-management event contract regressions."""

from copy import deepcopy

import pytest

from ea_core_foundation import ContractValidationError, validate_asyncapi_document
from ea_core_foundation import validation_data_management_closure as closure_validation

_SHARED_ENVELOPE = (
    "https://schemas.contextualwisdomlab.org/context/"
    "cloudevent-envelope.v1.schema.json"
)
_EVENTS = (
    (
        "dataManagementImprovementEvents",
        "publishDataManagementImprovementInitiativeCreated",
        "DataManagementImprovementInitiativeCreated",
        "org.contextualwisdomlab.ea.data_management.improvement_initiative_created.v1",
    ),
    (
        "dataManagementEvidenceAcceptedEvents",
        "publishDataManagementEvidenceAccepted",
        "DataManagementEvidenceAccepted",
        "org.contextualwisdomlab.ea.data_management.evidence_accepted.v1",
    ),
    (
        "dataManagementMilestoneCompletedEvents",
        "publishDataManagementMilestoneCompleted",
        "DataManagementMilestoneCompleted",
        "org.contextualwisdomlab.ea.data_management.milestone_completed.v1",
    ),
)


def _event_schema(document, message_name="DataManagementEvidenceAccepted"):
    """Return one event-specific schema for corruption regressions."""

    return document["components"]["messages"][message_name]["payload"]["schema"][
        "allOf"
    ][1]


@pytest.mark.parametrize(
    ("channel_name", "operation_name", "message_name", "event_type"),
    _EVENTS,
)
def test_checked_in_contract_publishes_data_management_event(
    asyncapi_document,
    channel_name: str,
    operation_name: str,
    message_name: str,
    event_type: str,
) -> None:
    """Every transactional outbox event is a first-class AsyncAPI contract."""

    assert validate_asyncapi_document(asyncapi_document) == 11
    channel = asyncapi_document["channels"][channel_name]
    assert channel == {
        "address": event_type,
        "messages": {message_name: {"$ref": f"#/components/messages/{message_name}"}},
    }
    operation = asyncapi_document["operations"][operation_name]
    assert operation == {
        "action": "send",
        "channel": {"$ref": f"#/channels/{channel_name}"},
        "messages": [{"$ref": f"#/channels/{channel_name}/messages/{message_name}"}],
    }
    message = asyncapi_document["components"]["messages"][message_name]
    assert message["contentType"] == "application/cloudevents+json"
    assert message["payload"]["schema"]["allOf"][0] == {"$ref": _SHARED_ENVELOPE}
    assert message["payload"]["schema"]["allOf"][1]["properties"]["type"] == {
        "const": event_type
    }


@pytest.mark.parametrize(
    ("collection_name", "event_index", "member_index"),
    [
        ("channels", event_index, 0)
        for event_index in range(len(_EVENTS))
    ]
    + [
        ("operations", event_index, 1)
        for event_index in range(len(_EVENTS))
    ]
    + [
        ("messages", event_index, 2)
        for event_index in range(len(_EVENTS))
    ],
)
def test_data_management_event_contract_fails_closed_when_member_is_missing(
    asyncapi_document,
    collection_name: str,
    event_index: int,
    member_index: int,
) -> None:
    """Removing any event binding makes deterministic contract validation fail."""

    member_name = _EVENTS[event_index][member_index]
    changed = deepcopy(asyncapi_document)
    if collection_name == "messages":
        del changed["components"]["messages"][member_name]
    else:
        del changed[collection_name][member_name]

    with pytest.raises(ContractValidationError) as error:
        validate_asyncapi_document(changed)

    assert member_name in str(error.value)


@pytest.mark.parametrize(
    ("corruption", "expected_message"),
    [
        ("non_object_registry", "components messages must be an object"),
        ("incomplete_registry", "event data contracts are incomplete"),
        ("invalid_all_of", "must combine the shared envelope and one event schema"),
        ("non_object_event_schema", "event schema must be an object"),
        ("missing_type_requirement", "must require type and data"),
        ("missing_data_schema", "requires an explicit data schema"),
        ("wrong_data_type", "data must be an object"),
        (
            "open_data_properties",
            "data must reject undeclared privacy-sensitive fields",
        ),
        ("non_object_data_properties", "data properties must be an object"),
        ("required_field_drift", "required data fields drifted"),
        ("allowed_field_drift", "allowed data fields drifted"),
    ],
)
def test_event_data_validator_fails_closed_on_malformed_contract_shapes(
    asyncapi_document,
    corruption: str,
    expected_message: str,
) -> None:
    """Malformed or privacy-expanding event data contracts fail closed."""

    changed = deepcopy(asyncapi_document)
    messages = changed["components"]["messages"]
    message_name = "DataManagementEvidenceAccepted"

    if corruption == "non_object_registry":
        changed["components"]["messages"] = []
    elif corruption == "incomplete_registry":
        messages.pop(message_name)
    elif corruption == "invalid_all_of":
        messages[message_name]["payload"]["schema"]["allOf"] = [{}]
    elif corruption == "non_object_event_schema":
        messages[message_name]["payload"]["schema"]["allOf"][1] = []
    else:
        event_schema = _event_schema(changed, message_name)
        data_schema = event_schema["properties"]["data"]
        if corruption == "missing_type_requirement":
            event_schema["required"] = ["data"]
        elif corruption == "missing_data_schema":
            event_schema["properties"] = []
        elif corruption == "wrong_data_type":
            data_schema["type"] = "array"
        elif corruption == "open_data_properties":
            data_schema["additionalProperties"] = True
        elif corruption == "non_object_data_properties":
            data_schema["properties"] = []
        elif corruption == "required_field_drift":
            data_schema["required"] = data_schema["required"][:-1]
        else:
            assert corruption == "allowed_field_drift"
            data_schema["properties"].pop(next(iter(data_schema["properties"])))

    with pytest.raises(ContractValidationError, match=expected_message):
        closure_validation._validate_event_data_contracts(changed)


def test_type_only_projection_skips_non_object_event_schema(asyncapi_document) -> None:
    """Layered validation leaves an unusable event schema for the validator to reject."""

    changed = deepcopy(asyncapi_document)
    message_name = "DataManagementEvidenceAccepted"
    changed["components"]["messages"][message_name]["payload"]["schema"]["allOf"][
        1
    ] = []

    projected = closure_validation._without_event_data_contracts(changed)

    assert (
        projected["components"]["messages"][message_name]["payload"]["schema"][
            "allOf"
        ][1]
        == []
    )


def test_type_only_projection_preserves_non_object_properties(asyncapi_document) -> None:
    """Layered validation removes only fields it can safely strip from an event schema."""

    changed = deepcopy(asyncapi_document)
    event_schema = _event_schema(changed)
    event_schema["properties"] = []

    projected = closure_validation._without_event_data_contracts(changed)
    projected_schema = _event_schema(projected)

    assert projected_schema["properties"] == []
    assert "required" not in projected_schema
