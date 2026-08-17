"""AsyncAPI foundation validation tests."""

import pytest

from ea_core_foundation import ContractValidationError, validate_asyncapi_document

_SHARED_ENVELOPE_SCHEMA = (
    "https://schemas.contextualwisdomlab.org/context/"
    "cloudevent-envelope.v1.schema.json"
)
_SHARED_SCHEMA_FORMAT = "application/schema+json;version=draft-2020-12"


def test_checked_in_asyncapi_contract_is_valid(asyncapi_document) -> None:
    """The checked-in contract defines every implemented publisher operation."""

    assert validate_asyncapi_document(asyncapi_document) == 3


def test_asyncapi_rejects_wrong_version(asyncapi_document) -> None:
    """The event contract uses one explicit AsyncAPI dialect."""

    asyncapi_document["asyncapi"] = "3.0.0"
    with pytest.raises(ContractValidationError, match="3.1.0"):
        validate_asyncapi_document(asyncapi_document)


@pytest.mark.parametrize(
    ("field_name", "field_value", "message"),
    [
        ("channels", [], "channels must be an object"),
        ("operations", [], "operations must be an object"),
    ],
)
def test_asyncapi_requires_mapping_fields(
    asyncapi_document, field_name, field_value, message
) -> None:
    """Channels and operations are JSON objects."""

    asyncapi_document[field_name] = field_value
    with pytest.raises(ContractValidationError, match=message):
        validate_asyncapi_document(asyncapi_document)


@pytest.mark.parametrize(
    ("channels", "operations"),
    [({}, {"publishObjectChanged": {"action": "send"}}), ({"events": {}}, {})],
)
def test_asyncapi_requires_nonempty_channels_and_operations(
    asyncapi_document, channels, operations
) -> None:
    """The document must contain both event addresses and publishers."""

    asyncapi_document["channels"] = channels
    asyncapi_document["operations"] = operations
    with pytest.raises(ContractValidationError, match="requires channels"):
        validate_asyncapi_document(asyncapi_document)


def test_asyncapi_rejects_single_word_operation_name(asyncapi_document) -> None:
    """Operation identities use at least two semantic words."""

    asyncapi_document["operations"] = {"publish": {"action": "send"}}
    with pytest.raises(ContractValidationError, match="operation name"):
        validate_asyncapi_document(asyncapi_document)


def test_asyncapi_rejects_non_object_operation(asyncapi_document) -> None:
    """Each operation must be represented by an object."""

    asyncapi_document["operations"] = {"publishObject": []}
    with pytest.raises(ContractValidationError, match="operation publishObject"):
        validate_asyncapi_document(asyncapi_document)


def test_asyncapi_initial_operations_are_publish_only(asyncapi_document) -> None:
    """The implemented contract exposes publisher operations only."""

    asyncapi_document["operations"]["publishObjectChanged"]["action"] = "receive"
    with pytest.raises(ContractValidationError, match="must publish"):
        validate_asyncapi_document(asyncapi_document)


def test_asyncapi_requires_components_object(asyncapi_document) -> None:
    """Components must be a JSON object before messages are inspected."""

    asyncapi_document["components"] = []
    with pytest.raises(ContractValidationError, match="components must be an object"):
        validate_asyncapi_document(asyncapi_document)


def test_asyncapi_requires_messages_object(asyncapi_document) -> None:
    """Messages must be represented as a JSON object."""

    asyncapi_document["components"] = {"messages": []}
    with pytest.raises(ContractValidationError, match="messages must be an object"):
        validate_asyncapi_document(asyncapi_document)


def test_asyncapi_requires_at_least_one_message(asyncapi_document) -> None:
    """Publisher operations require a message schema registry."""

    asyncapi_document["components"]["messages"] = {}
    with pytest.raises(ContractValidationError, match="requires message schemas"):
        validate_asyncapi_document(asyncapi_document)


def test_asyncapi_messages_reuse_shared_context_graph_envelope(
    asyncapi_document,
) -> None:
    """EA event payloads extend, rather than redefine, the shared envelope."""

    for message_name, message in asyncapi_document["components"]["messages"].items():
        payload = message["payload"]
        assert payload["schemaFormat"] == _SHARED_SCHEMA_FORMAT, message_name
        assert payload["schema"]["allOf"][0] == {"$ref": _SHARED_ENVELOPE_SCHEMA}

    assert asyncapi_document["components"]["messages"]["ArchitectureObjectChanged"][
        "payload"
    ]["schema"]["allOf"][1]["properties"]["type"] == {
        "const": "org.contextualwisdomlab.ea.object.changed.v1"
    }
    assert asyncapi_document["components"]["messages"]["LifecycleChanged"]["payload"][
        "schema"
    ]["allOf"][1]["properties"]["type"] == {
        "const": "org.contextualwisdomlab.ea.lifecycle.changed.v1"
    }
    assert asyncapi_document["components"]["messages"]["TransformationApproved"][
        "payload"
    ]["schema"]["allOf"][1]["properties"]["type"] == {
        "const": "org.contextualwisdomlab.ea.transformation.approved.v1"
    }


def test_asyncapi_rejects_local_duplicate_envelope(asyncapi_document) -> None:
    """A local envelope copy cannot silently drift from Context Graph Contracts."""

    asyncapi_document["components"]["messages"]["ArchitectureObjectChanged"][
        "payload"
    ] = {"type": "object", "properties": {"id": {"type": "string"}}}

    with pytest.raises(ContractValidationError, match="shared Context Graph envelope"):
        validate_asyncapi_document(asyncapi_document)
