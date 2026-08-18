"""AsyncAPI foundation validation tests."""

import pytest

from ea_core_foundation import ContractValidationError, validate_asyncapi_document

_SHARED_ENVELOPE_SCHEMA = (
    "https://schemas.contextualwisdomlab.org/context/"
    "cloudevent-envelope.v1.schema.json"
)
_SHARED_SCHEMA_FORMAT = "application/schema+json;version=draft-2020-12"
_EVENT_CONTRACTS = {
    "ArchitectureObjectChanged": (
        "org.contextualwisdomlab.ea.object.changed.v1",
        {
            "architecture_object_id",
            "object_revision_id",
            "truth_status_code",
            "valid_from",
            "recorded_at",
        },
    ),
    "LifecycleChanged": (
        "org.contextualwisdomlab.ea.lifecycle.changed.v1",
        {
            "architecture_object_id",
            "lifecycle_interval_id",
            "lifecycle_phase_id",
            "valid_from",
            "recorded_at",
        },
    ),
    "TransformationApproved": (
        "org.contextualwisdomlab.ea.transformation.approved.v1",
        {
            "architecture_transformation_id",
            "transformation_history_record_id",
            "decision_request_id",
            "effective_at",
            "evidence_record_id",
            "transformation_state_code",
        },
    ),
    "TransformationScheduled": (
        "org.contextualwisdomlab.ea.transformation.scheduled.v1",
        {
            "architecture_transformation_id",
            "transformation_schedule_record_id",
            "initiative_milestone_id",
            "decision_request_id",
            "effective_at",
            "milestone_target_at",
            "evidence_record_id",
        },
    ),
    "TransformationStarted": (
        "org.contextualwisdomlab.ea.transformation.started.v1",
        {
            "architecture_transformation_id",
            "transformation_history_record_id",
            "decision_request_id",
            "effective_at",
            "evidence_record_id",
            "transformation_state_code",
        },
    ),
    "TransformationCompleted": (
        "org.contextualwisdomlab.ea.transformation.completed.v1",
        {
            "architecture_transformation_id",
            "transformation_history_record_id",
            "decision_request_id",
            "effective_at",
            "evidence_record_id",
            "transformation_state_code",
        },
    ),
    "TransformationVerificationRecorded": (
        "org.contextualwisdomlab.ea.transformation.verification_recorded.v1",
        {
            "architecture_transformation_id",
            "transformation_history_record_id",
            "decision_request_id",
            "effective_at",
            "evidence_record_id",
            "verification_outcome_code",
        },
    ),
    "TransformationReplanned": (
        "org.contextualwisdomlab.ea.transformation.replanned.v1",
        {
            "predecessor_architecture_transformation_id",
            "replacement_architecture_transformation_id",
            "transformation_replan_record_id",
            "transformation_history_record_id",
            "decision_request_id",
            "effective_at",
            "evidence_record_id",
        },
    ),
    "DataManagementImprovementInitiativeCreated": (
        "org.contextualwisdomlab.ea.data_management."
        "improvement_initiative_created.v1",
        {
            "assessment_result_uri",
            "missing_evidence_code",
            "target_capability_object_id",
            "accountable_organization_object_id",
            "remediation_initiative_id",
            "initiative_milestone_id",
            "decision_request_id",
            "due_at",
            "source_truth_status_code",
            "initiative_truth_status_code",
            "next_action",
        },
    ),
    "DataManagementEvidenceAccepted": (
        "org.contextualwisdomlab.ea.data_management.evidence_accepted.v1",
        {
            "assessment_improvement_plan_id",
            "data_management_assessment_projection_id",
            "missing_evidence_code",
            "assessment_evidence_acceptance_id",
            "evidence_uri",
            "evidence_truth_status_code",
            "evidence_sha256",
            "accepted_at",
            "next_action",
        },
    ),
    "DataManagementMilestoneCompleted": (
        "org.contextualwisdomlab.ea.data_management.milestone_completed.v1",
        {
            "assessment_improvement_plan_id",
            "initiative_milestone_id",
            "milestone_completion_record_id",
            "assessment_evidence_acceptance_id",
            "causation_event_id",
            "completed_at",
            "next_action",
        },
    ),
}


def test_checked_in_asyncapi_contract_is_valid(asyncapi_document) -> None:
    """The checked-in contract defines every implemented publisher operation."""

    assert validate_asyncapi_document(asyncapi_document) == 11


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
    """Messages must be represented as a JSON object before inspection."""

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

    for message_name, (event_type, _) in _EVENT_CONTRACTS.items():
        message = asyncapi_document["components"]["messages"][message_name]
        assert message["payload"]["schema"]["allOf"][1]["properties"]["type"] == {
            "const": event_type
        }


def test_asyncapi_event_data_is_explicit_and_privacy_minimized(
    asyncapi_document,
) -> None:
    """Every publisher binds its buyer-relevant identifiers without extra raw data."""

    messages = asyncapi_document["components"]["messages"]
    assert set(messages) == set(_EVENT_CONTRACTS)
    for message_name, (_, required_fields) in _EVENT_CONTRACTS.items():
        event_schema = messages[message_name]["payload"]["schema"]["allOf"][1]
        assert set(event_schema["required"]) == {"type", "data"}, message_name
        data_schema = event_schema["properties"]["data"]
        assert data_schema["type"] == "object", message_name
        assert data_schema["additionalProperties"] is False, message_name
        assert set(data_schema["required"]) == required_fields, message_name
        assert set(data_schema["properties"]) == required_fields, message_name


def test_asyncapi_rejects_local_duplicate_envelope(asyncapi_document) -> None:
    """A local envelope copy cannot silently drift from Context Graph Contracts."""

    asyncapi_document["components"]["messages"]["ArchitectureObjectChanged"][
        "payload"
    ] = {"type": "object", "properties": {"id": {"type": "string"}}}

    with pytest.raises(ContractValidationError, match="shared Context Graph envelope"):
        validate_asyncapi_document(asyncapi_document)
