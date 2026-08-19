"""Validation extension for data-management evidence-closure interoperability."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from . import validation as execution_validation
from . import validation_data_management as base

ContractValidationError = base.ContractValidationError
RepositoryReport = base.RepositoryReport
validate_connector_catalog = base.validate_connector_catalog
validate_migration_inventory = base.validate_migration_inventory
validate_migration_sql = base.validate_migration_sql
validate_openapi_document = base.validate_openapi_document
validate_openapi_runtime_surface = base.validate_openapi_runtime_surface

_DATA_MANAGEMENT_CLOSURE_EVENTS = (
    (
        "dataManagementEvidenceAcceptedEvents",
        "publishDataManagementEvidenceAccepted",
        "DataManagementEvidenceAccepted",
        "org.contextualwisdomlab.ea.data_management.evidence_accepted.v1",
        "data-management evidence acceptance",
    ),
    (
        "dataManagementMilestoneCompletedEvents",
        "publishDataManagementMilestoneCompleted",
        "DataManagementMilestoneCompleted",
        "org.contextualwisdomlab.ea.data_management.milestone_completed.v1",
        "data-management milestone completion",
    ),
)
_EVENT_DATA_FIELDS: dict[str, frozenset[str]] = {
    "ArchitectureObjectChanged": frozenset(
        {
            "architecture_object_id",
            "object_revision_id",
            "truth_status_code",
            "valid_from",
            "recorded_at",
        }
    ),
    "LifecycleChanged": frozenset(
        {
            "architecture_object_id",
            "lifecycle_interval_id",
            "lifecycle_phase_id",
            "valid_from",
            "recorded_at",
        }
    ),
    "TransformationApproved": frozenset(
        {
            "architecture_transformation_id",
            "transformation_history_record_id",
            "decision_request_id",
            "effective_at",
            "evidence_record_id",
            "transformation_state_code",
        }
    ),
    "TransformationScheduled": frozenset(
        {
            "architecture_transformation_id",
            "transformation_schedule_record_id",
            "initiative_milestone_id",
            "decision_request_id",
            "effective_at",
            "milestone_target_at",
            "evidence_record_id",
        }
    ),
    "TransformationStarted": frozenset(
        {
            "architecture_transformation_id",
            "transformation_history_record_id",
            "decision_request_id",
            "effective_at",
            "evidence_record_id",
            "transformation_state_code",
        }
    ),
    "TransformationCompleted": frozenset(
        {
            "architecture_transformation_id",
            "transformation_history_record_id",
            "decision_request_id",
            "effective_at",
            "evidence_record_id",
            "transformation_state_code",
        }
    ),
    "TransformationVerificationRecorded": frozenset(
        {
            "architecture_transformation_id",
            "transformation_history_record_id",
            "decision_request_id",
            "effective_at",
            "evidence_record_id",
            "verification_outcome_code",
        }
    ),
    "TransformationReplanned": frozenset(
        {
            "predecessor_architecture_transformation_id",
            "replacement_architecture_transformation_id",
            "transformation_replan_record_id",
            "transformation_history_record_id",
            "decision_request_id",
            "effective_at",
            "evidence_record_id",
        }
    ),
    "DataManagementImprovementInitiativeCreated": frozenset(
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
        }
    ),
    "DataManagementEvidenceAccepted": frozenset(
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
        }
    ),
    "DataManagementMilestoneCompleted": frozenset(
        {
            "assessment_improvement_plan_id",
            "initiative_milestone_id",
            "milestone_completion_record_id",
            "assessment_evidence_acceptance_id",
            "causation_event_id",
            "completed_at",
            "next_action",
        }
    ),
}


def _without_event_data_contracts(document: dict[str, Any]) -> dict[str, Any]:
    """Return the preceding type-only event view for layered validation."""

    changed = deepcopy(document)
    components = changed.get("components")
    messages = components.get("messages") if isinstance(components, dict) else None
    if not isinstance(messages, dict):
        return changed
    for message_name in _EVENT_DATA_FIELDS:
        message = messages.get(message_name)
        if not isinstance(message, dict):
            continue
        payload = message.get("payload")
        schema = payload.get("schema") if isinstance(payload, dict) else None
        all_of = schema.get("allOf") if isinstance(schema, dict) else None
        if not isinstance(all_of, list) or len(all_of) < 2:
            continue
        event_schema = all_of[1]
        if not isinstance(event_schema, dict):
            continue
        properties = event_schema.get("properties")
        if isinstance(properties, dict):
            properties.pop("data", None)
        event_schema.pop("required", None)
    return changed


def _validate_event_data_contracts(document: dict[str, Any]) -> None:
    """Require exact event-specific data fields and reject undeclared raw data."""

    components = document.get("components")
    messages = components.get("messages") if isinstance(components, dict) else None
    if not isinstance(messages, dict):
        raise ContractValidationError("AsyncAPI components messages must be an object")
    if set(messages) != set(_EVENT_DATA_FIELDS):
        raise ContractValidationError("AsyncAPI event data contracts are incomplete")
    for message_name, required_fields in _EVENT_DATA_FIELDS.items():
        message = messages.get(message_name)
        payload = message.get("payload") if isinstance(message, dict) else None
        schema = payload.get("schema") if isinstance(payload, dict) else None
        all_of = schema.get("allOf") if isinstance(schema, dict) else None
        if not isinstance(all_of, list) or len(all_of) != 2:
            raise ContractValidationError(
                f"{message_name} must combine the shared envelope and one event schema"
            )
        event_schema = all_of[1]
        if not isinstance(event_schema, dict):
            raise ContractValidationError(
                f"{message_name} event schema must be an object"
            )
        if set(event_schema.get("required", ())) != {"type", "data"}:
            raise ContractValidationError(f"{message_name} must require type and data")
        properties = event_schema.get("properties")
        data_schema = properties.get("data") if isinstance(properties, dict) else None
        if not isinstance(data_schema, dict):
            raise ContractValidationError(
                f"{message_name} requires an explicit data schema"
            )
        if data_schema.get("type") != "object":
            raise ContractValidationError(f"{message_name} data must be an object")
        if data_schema.get("additionalProperties") is not False:
            raise ContractValidationError(
                f"{message_name} data must reject undeclared privacy-sensitive fields"
            )
        data_properties = data_schema.get("properties")
        if not isinstance(data_properties, dict):
            raise ContractValidationError(
                f"{message_name} data properties must be an object"
            )
        if set(data_schema.get("required", ())) != required_fields:
            raise ContractValidationError(
                f"{message_name} required data fields drifted"
            )
        if set(data_properties) != required_fields:
            raise ContractValidationError(f"{message_name} allowed data fields drifted")


def _without_data_management_closure_asyncapi(
    document: dict[str, Any],
) -> dict[str, Any]:
    """Return the prior event generation without evidence-closure publications."""

    changed = deepcopy(document)
    channels = changed.get("channels")
    operations = changed.get("operations")
    components = changed.get("components")
    messages = components.get("messages") if isinstance(components, dict) else None
    for channel_name, operation_name, message_name, _, _ in (
        _DATA_MANAGEMENT_CLOSURE_EVENTS
    ):
        if isinstance(channels, dict):
            channels.pop(channel_name, None)
        if isinstance(operations, dict):
            operations.pop(operation_name, None)
        if isinstance(messages, dict):
            messages.pop(message_name, None)
    return changed


def validate_asyncapi_document(document: dict[str, Any]) -> int:
    """Validate improvement creation plus receipt-bound closure publications."""

    type_only_document = _without_event_data_contracts(document)
    legacy_operation_count = base.validate_asyncapi_document(
        _without_data_management_closure_asyncapi(type_only_document)
    )
    for channel_name, operation_name, message_name, event_type, command_name in (
        _DATA_MANAGEMENT_CLOSURE_EVENTS
    ):
        execution_validation._validate_execution_event(
            type_only_document,
            channel_name=channel_name,
            operation_name=operation_name,
            message_name=message_name,
            event_type=event_type,
            command_name=command_name,
        )
    _validate_event_data_contracts(document)
    return legacy_operation_count + len(_DATA_MANAGEMENT_CLOSURE_EVENTS)


def validate_repository(repository_root: Path) -> RepositoryReport:
    """Validate repository artifacts with data-management closure contracts."""

    migration_directory = repository_root / "database/migrations"
    openapi_path = repository_root / "contracts/openapi.json"
    asyncapi_path = repository_root / "contracts/asyncapi.json"
    connector_path = repository_root / "contracts/connectors/ecosystem.json"
    for required_path in (openapi_path, asyncapi_path, connector_path):
        if not required_path.is_file():
            raise ContractValidationError(f"missing required file: {required_path}")
    migration_paths = tuple(sorted(migration_directory.glob("*.sql")))
    validate_migration_inventory(migration_paths)
    migration_text = "\n".join(
        migration_path.read_text(encoding="utf-8")
        for migration_path in migration_paths
    )
    table_count, column_count, index_count, constraint_count = validate_migration_sql(
        migration_text
    )
    openapi_document = json.loads(openapi_path.read_text(encoding="utf-8"))
    openapi_operation_count = validate_openapi_document(openapi_document)
    validate_openapi_runtime_surface(openapi_document)
    asyncapi_operation_count = validate_asyncapi_document(
        json.loads(asyncapi_path.read_text(encoding="utf-8"))
    )
    connector_count = validate_connector_catalog(
        json.loads(connector_path.read_text(encoding="utf-8"))
    )
    adr_count = len(tuple((repository_root / "docs/adr").glob("*.md")))
    if adr_count < 10:
        raise ContractValidationError("the foundation requires at least ten ADRs")
    return RepositoryReport(
        table_count=table_count,
        column_count=column_count,
        index_count=index_count,
        constraint_count=constraint_count,
        openapi_operation_count=openapi_operation_count,
        asyncapi_operation_count=asyncapi_operation_count,
        adr_count=adr_count,
        connector_count=connector_count,
    )
