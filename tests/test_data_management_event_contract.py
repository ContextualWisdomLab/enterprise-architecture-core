"""Data-management improvement event contract regressions."""

from copy import deepcopy

import pytest

from ea_core_foundation import ContractValidationError, validate_asyncapi_document

_EVENT_TYPE = (
    "org.contextualwisdomlab.ea.data_management.improvement_initiative_created.v1"
)
_CHANNEL_NAME = "dataManagementImprovementEvents"
_OPERATION_NAME = "publishDataManagementImprovementInitiativeCreated"
_MESSAGE_NAME = "DataManagementImprovementInitiativeCreated"
_SHARED_ENVELOPE = (
    "https://schemas.contextualwisdomlab.org/context/"
    "cloudevent-envelope.v1.schema.json"
)


def test_checked_in_contract_publishes_improvement_initiative_event(
    asyncapi_document,
) -> None:
    """The outbox event is a first-class AsyncAPI contract, not hidden SQL."""

    assert validate_asyncapi_document(asyncapi_document) == 9
    channel = asyncapi_document["channels"][_CHANNEL_NAME]
    assert channel == {
        "address": _EVENT_TYPE,
        "messages": {_MESSAGE_NAME: {"$ref": f"#/components/messages/{_MESSAGE_NAME}"}},
    }
    operation = asyncapi_document["operations"][_OPERATION_NAME]
    assert operation == {
        "action": "send",
        "channel": {"$ref": f"#/channels/{_CHANNEL_NAME}"},
        "messages": [{"$ref": f"#/channels/{_CHANNEL_NAME}/messages/{_MESSAGE_NAME}"}],
    }
    message = asyncapi_document["components"]["messages"][_MESSAGE_NAME]
    assert message["contentType"] == "application/cloudevents+json"
    assert message["payload"]["schema"]["allOf"][0] == {"$ref": _SHARED_ENVELOPE}
    assert message["payload"]["schema"]["allOf"][1]["properties"]["type"] == {
        "const": _EVENT_TYPE
    }


@pytest.mark.parametrize(
    ("collection_name", "member_name"),
    [
        ("channels", _CHANNEL_NAME),
        ("operations", _OPERATION_NAME),
        ("messages", _MESSAGE_NAME),
    ],
)
def test_improvement_event_contract_fails_closed_when_member_is_missing(
    asyncapi_document,
    collection_name: str,
    member_name: str,
) -> None:
    """Removing any event binding makes deterministic contract validation fail."""

    changed = deepcopy(asyncapi_document)
    if collection_name == "messages":
        del changed["components"]["messages"][member_name]
    else:
        del changed[collection_name][member_name]

    with pytest.raises(ContractValidationError, match="data-management improvement"):
        validate_asyncapi_document(changed)
