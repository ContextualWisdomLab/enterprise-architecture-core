"""Validation extension for data-management improvement event interoperability."""

from __future__ import annotations

import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any

from . import validation as execution_validation
from . import validation_core as core
from . import validation_replan as base

ContractValidationError = base.ContractValidationError
RepositoryReport = base.RepositoryReport
validate_connector_catalog = base.validate_connector_catalog
validate_migration_inventory = base.validate_migration_inventory
validate_openapi_document = base.validate_openapi_document
validate_openapi_runtime_surface = base.validate_openapi_runtime_surface

_DATA_MANAGEMENT_IMPROVEMENT_MESSAGE_NAME = (
    "DataManagementImprovementInitiativeCreated"
)
_DATA_MANAGEMENT_IMPROVEMENT_CHANNEL_NAME = "dataManagementImprovementEvents"
_DATA_MANAGEMENT_IMPROVEMENT_OPERATION_NAME = (
    "publishDataManagementImprovementInitiativeCreated"
)
_DATA_MANAGEMENT_IMPROVEMENT_EVENT_TYPE = (
    "org.contextualwisdomlab.ea.data_management.improvement_initiative_created.v1"
)
_ALTER_ADD_COLUMN_PATTERN = re.compile(
    r"\bADD\s+COLUMN\s+(?:IF\s+NOT\s+EXISTS\s+)?"
    r"(?P<column>[a-z][a-z0-9_]*)\s+"
    r"(?:uuid|text|integer|boolean|timestamptz|date|numeric|jsonb)\b",
    re.IGNORECASE,
)
_CONSTRAINT_COMMENT_PREFIX_PATTERN = re.compile(
    r"\bCOMMENT\s+ON\s+CONSTRAINT\b",
    re.IGNORECASE,
)


def validate_migration_sql(sql_text: str) -> tuple[int, int, int, int]:
    """Validate migrations and report ALTER columns without counting SQL comments."""

    inventory_text = _CONSTRAINT_COMMENT_PREFIX_PATTERN.sub(
        "COMMENT ON documented_object",
        sql_text,
    )
    table_count, column_count, index_count, constraint_count = (
        base.validate_migration_sql(inventory_text)
    )
    altered_columns = [
        match.group("column").lower()
        for match in _ALTER_ADD_COLUMN_PATTERN.finditer(sql_text)
    ]
    for column_name in altered_columns:
        core._require_two_word_name(column_name, "column")
    return (
        table_count,
        column_count + len(altered_columns),
        index_count,
        constraint_count,
    )


def _without_data_management_asyncapi(document: dict[str, Any]) -> dict[str, Any]:
    """Return the previous event contract without the assessment-improvement event."""

    changed = deepcopy(document)
    channels = changed.get("channels")
    if isinstance(channels, dict):
        channels.pop(_DATA_MANAGEMENT_IMPROVEMENT_CHANNEL_NAME, None)
    operations = changed.get("operations")
    if isinstance(operations, dict):
        operations.pop(_DATA_MANAGEMENT_IMPROVEMENT_OPERATION_NAME, None)
    components = changed.get("components")
    messages = components.get("messages") if isinstance(components, dict) else None
    if isinstance(messages, dict):
        messages.pop(_DATA_MANAGEMENT_IMPROVEMENT_MESSAGE_NAME, None)
    return changed


def validate_asyncapi_document(document: dict[str, Any]) -> int:
    """Validate the full event surface including assessment-improvement creation."""

    legacy_operation_count = base.validate_asyncapi_document(
        _without_data_management_asyncapi(document)
    )
    execution_validation._validate_execution_event(
        document,
        channel_name=_DATA_MANAGEMENT_IMPROVEMENT_CHANNEL_NAME,
        operation_name=_DATA_MANAGEMENT_IMPROVEMENT_OPERATION_NAME,
        message_name=_DATA_MANAGEMENT_IMPROVEMENT_MESSAGE_NAME,
        event_type=_DATA_MANAGEMENT_IMPROVEMENT_EVENT_TYPE,
        command_name="data-management improvement",
    )
    return legacy_operation_count + 1


def validate_repository(repository_root: Path) -> RepositoryReport:
    """Validate repository artifacts with data-management improvement contracts."""

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
