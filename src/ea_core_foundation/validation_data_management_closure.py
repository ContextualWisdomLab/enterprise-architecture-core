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

    legacy_operation_count = base.validate_asyncapi_document(
        _without_data_management_closure_asyncapi(document)
    )
    for channel_name, operation_name, message_name, event_type, command_name in (
        _DATA_MANAGEMENT_CLOSURE_EVENTS
    ):
        execution_validation._validate_execution_event(
            document,
            channel_name=channel_name,
            operation_name=operation_name,
            message_name=message_name,
            event_type=event_type,
            command_name=command_name,
        )
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
