"""Validation extension for executable target-state replanning contracts."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from . import validation as base
from . import validation_core as core

ContractValidationError = base.ContractValidationError
RepositoryReport = base.RepositoryReport
validate_connector_catalog = base.validate_connector_catalog
validate_migration_inventory = base.validate_migration_inventory
validate_migration_sql = base.validate_migration_sql

_TARGET_STATE_REPLAN_RUNTIME_PATH = (
    "/v1/architecture-transformations/{architecture_transformation_id}/replan"
)
_TARGET_STATE_REPLAN_OPERATION_ID = "replanTechnologyTargetState"
_TARGET_STATE_REPLAN_MESSAGE_NAME = "TransformationReplanned"
_TARGET_STATE_REPLAN_CHANNEL_NAME = "transformationReplanEvents"
_TARGET_STATE_REPLAN_OPERATION_NAME = "publishTransformationReplanned"
_TARGET_STATE_REPLAN_EVENT_TYPE = (
    "org.contextualwisdomlab.ea.transformation.replanned.v1"
)
_TARGET_STATE_REPLAN_ROLE_CONFIGURATION = "EA_REPLAN_ROLES"
_TARGET_STATE_REPLAN_REQUEST_SCHEMA = "TargetStateReplanRequest"
_TARGET_STATE_REPLAN_RECEIPT_SCHEMA = "TargetStateReplanReceipt"


def _without_replan_role(document: dict[str, Any]) -> dict[str, Any]:
    """Return the prior contract view with the replanning role removed."""

    changed = deepcopy(document)
    try:
        configuration = changed["x-keyverse-contract"]["requiredConfiguration"]
    except (KeyError, TypeError):
        return changed
    if not isinstance(configuration, list):
        return changed
    if _TARGET_STATE_REPLAN_ROLE_CONFIGURATION not in configuration:
        raise ContractValidationError(
            "x-keyverse-contract requiredConfiguration must include EA_REPLAN_ROLES"
        )
    changed["x-keyverse-contract"]["requiredConfiguration"] = [
        value
        for value in configuration
        if value != _TARGET_STATE_REPLAN_ROLE_CONFIGURATION
    ]
    return changed


def validate_openapi_document(document: dict[str, Any]) -> int:
    """Validate OpenAPI plus the distinct purpose-bound replanning role."""

    return base.validate_openapi_document(_without_replan_role(document))


def validate_openapi_runtime_surface(document: dict[str, Any]) -> None:
    """Require the replanning operation in addition to every earlier runtime path."""

    changed = deepcopy(document)
    paths = core._require_mapping(changed.get("paths"), "paths")
    schemas = core._require_mapping(
        core._require_mapping(changed.get("components"), "components").get("schemas"),
        "schemas",
    )
    for schema_name in (
        _TARGET_STATE_REPLAN_REQUEST_SCHEMA,
        _TARGET_STATE_REPLAN_RECEIPT_SCHEMA,
    ):
        if schema_name not in schemas:
            raise ContractValidationError(f"missing OpenAPI schemas: {schema_name}")
    base._validate_execution_operation(
        paths,
        runtime_path=_TARGET_STATE_REPLAN_RUNTIME_PATH,
        operation_id=_TARGET_STATE_REPLAN_OPERATION_ID,
        command_name="replan",
        request_schema=_TARGET_STATE_REPLAN_REQUEST_SCHEMA,
        receipt_schema=_TARGET_STATE_REPLAN_RECEIPT_SCHEMA,
    )
    paths.pop(_TARGET_STATE_REPLAN_RUNTIME_PATH)
    schemas.pop(_TARGET_STATE_REPLAN_REQUEST_SCHEMA)
    schemas.pop(_TARGET_STATE_REPLAN_RECEIPT_SCHEMA)
    base.validate_openapi_runtime_surface(changed)


def validate_asyncapi_document(document: dict[str, Any]) -> int:
    """Validate every earlier event plus the replanning transactional outbox event."""

    changed = deepcopy(document)
    channels = core._require_mapping(changed.get("channels"), "channels")
    operations = core._require_mapping(changed.get("operations"), "operations")
    components = core._require_mapping(changed.get("components"), "components")
    messages = core._require_mapping(components.get("messages"), "messages")
    base._validate_execution_event(
        document,
        channel_name=_TARGET_STATE_REPLAN_CHANNEL_NAME,
        operation_name=_TARGET_STATE_REPLAN_OPERATION_NAME,
        message_name=_TARGET_STATE_REPLAN_MESSAGE_NAME,
        event_type=_TARGET_STATE_REPLAN_EVENT_TYPE,
        command_name="replan",
    )
    channels.pop(_TARGET_STATE_REPLAN_CHANNEL_NAME, None)
    operations.pop(_TARGET_STATE_REPLAN_OPERATION_NAME, None)
    messages.pop(_TARGET_STATE_REPLAN_MESSAGE_NAME, None)
    return base.validate_asyncapi_document(changed) + 1


def validate_repository(repository_root: Path) -> RepositoryReport:
    """Validate the repository using the complete replanning-aware contract surface."""

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
