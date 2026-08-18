"""Data-management event contract regressions."""

from copy import deepcopy

import pytest

from ea_core_foundation import ContractValidationError, validate_asyncapi_document

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
