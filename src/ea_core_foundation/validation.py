"""Deterministic validation for the complete EA Core contract surface."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from . import validation_core as core

ContractValidationError = core.ContractValidationError
RepositoryReport = core.RepositoryReport
validate_connector_catalog = core.validate_connector_catalog
validate_migration_inventory = core.validate_migration_inventory
validate_migration_sql = core.validate_migration_sql

_TARGET_STATE_SCHEDULE_RUNTIME_PATH = (
    "/v1/architecture-transformations/{architecture_transformation_id}/schedule"
)
_TARGET_STATE_SCHEDULE_OPERATION_ID = "scheduleTechnologyTargetState"
_TARGET_STATE_SCHEDULE_MESSAGE_NAME = "TransformationScheduled"
_TARGET_STATE_SCHEDULE_CHANNEL_NAME = "transformationScheduleEvents"
_TARGET_STATE_SCHEDULE_OPERATION_NAME = "publishTransformationScheduled"
_TARGET_STATE_SCHEDULE_EVENT_TYPE = (
    "org.contextualwisdomlab.ea.transformation.scheduled.v1"
)
_TARGET_STATE_START_RUNTIME_PATH = (
    "/v1/architecture-transformations/{architecture_transformation_id}/start"
)
_TARGET_STATE_START_OPERATION_ID = "startTechnologyTargetState"
_TARGET_STATE_START_MESSAGE_NAME = "TransformationStarted"
_TARGET_STATE_START_CHANNEL_NAME = "transformationStartEvents"
_TARGET_STATE_START_OPERATION_NAME = "publishTransformationStarted"
_TARGET_STATE_START_EVENT_TYPE = "org.contextualwisdomlab.ea.transformation.started.v1"
_EXECUTION_ROLE_CONFIGURATION = frozenset({"EA_SCHEDULE_ROLES", "EA_START_ROLES"})


def _without_execution_roles(document: dict[str, Any]) -> dict[str, Any]:
    """Return a legacy-core validation view with execution-role extensions removed."""

    changed = deepcopy(document)
    configuration = changed["x-keyverse-contract"]["requiredConfiguration"]
    missing_configuration = _EXECUTION_ROLE_CONFIGURATION.difference(configuration)
    if missing_configuration:
        missing = sorted(missing_configuration)[0]
        raise ContractValidationError(
            f"x-keyverse-contract requiredConfiguration must include {missing}"
        )
    changed["x-keyverse-contract"]["requiredConfiguration"] = [
        value
        for value in configuration
        if value not in _EXECUTION_ROLE_CONFIGURATION
    ]
    return changed


def validate_openapi_document(document: dict[str, Any]) -> int:
    """Validate generic OpenAPI rules plus purpose-bound execution role extensions."""

    try:
        changed = _without_execution_roles(document)
    except (KeyError, TypeError):
        return core.validate_openapi_document(document)
    return core.validate_openapi_document(changed)


def _validate_execution_operation(
    paths: dict[str, Any],
    *,
    runtime_path: str,
    operation_id: str,
    command_name: str,
    request_schema: str,
    receipt_schema: str,
) -> None:
    """Bind one governed execution OpenAPI operation to executable behavior."""

    path_item = core._require_mapping(
        paths.get(runtime_path),
        f"path {runtime_path}",
    )
    operation = core._require_mapping(
        path_item.get("post"),
        f"{runtime_path} post",
    )
    if operation.get("operationId") != operation_id:
        raise ContractValidationError(
            f"target-state {command_name} operationId must be {operation_id}"
        )
    if operation.get("security") != [{"keyverseBearer": []}]:
        raise ContractValidationError(
            f"target-state {command_name} must require Keyverse bearer authorization"
        )
    parameters = core._parameter_index(operation)
    if set(parameters) != {("architecture_transformation_id", "path")}:
        raise ContractValidationError(
            f"target-state {command_name} parameters must match executable request parsing"
        )
    core._require_parameter(
        parameters,
        ("architecture_transformation_id", "path"),
        required=True,
        schema={"type": "string", "format": "uuid"},
    )
    expected_request_body = {
        "required": True,
        "content": {
            "application/json": {
                "schema": {"$ref": f"#/components/schemas/{request_schema}"}
            }
        },
    }
    if operation.get("requestBody") != expected_request_body:
        raise ContractValidationError(
            f"target-state {command_name} request body must match executable JSON parsing"
        )
    for status_code in ("200", "201"):
        core._require_json_schema_ref(
            operation,
            runtime_path,
            status_code,
            receipt_schema,
        )
    for status_code in ("400", "401", "403", "503"):
        core._require_json_schema_ref(
            operation,
            runtime_path,
            status_code,
            "ErrorStatus",
        )


def validate_openapi_runtime_surface(document: dict[str, Any]) -> None:
    """Require planner, approval, schedule, and start surfaces to match runtime code."""

    paths = core._require_mapping(document.get("paths"), "paths")
    _validate_execution_operation(
        paths,
        runtime_path=_TARGET_STATE_SCHEDULE_RUNTIME_PATH,
        operation_id=_TARGET_STATE_SCHEDULE_OPERATION_ID,
        command_name="schedule",
        request_schema="TargetStateScheduleRequest",
        receipt_schema="TargetStateScheduleReceipt",
    )
    _validate_execution_operation(
        paths,
        runtime_path=_TARGET_STATE_START_RUNTIME_PATH,
        operation_id=_TARGET_STATE_START_OPERATION_ID,
        command_name="start",
        request_schema="TargetStateStartRequest",
        receipt_schema="TargetStateStartReceipt",
    )
    schemas = core._require_mapping(
        core._require_mapping(document.get("components"), "components").get("schemas"),
        "schemas",
    )
    required_execution_schemas = {
        "TargetStateScheduleRequest",
        "TargetStateScheduleReceipt",
        "TargetStateStartRequest",
        "TargetStateStartReceipt",
    }
    missing_schemas = required_execution_schemas.difference(schemas)
    if missing_schemas:
        raise ContractValidationError(
            f"missing OpenAPI schemas: {sorted(missing_schemas)!r}"
        )
    changed = deepcopy(document)
    for runtime_path in (
        _TARGET_STATE_SCHEDULE_RUNTIME_PATH,
        _TARGET_STATE_START_RUNTIME_PATH,
    ):
        changed["paths"].pop(runtime_path)
    for schema_name in required_execution_schemas:
        changed["components"]["schemas"].pop(schema_name)
    core.validate_openapi_runtime_surface(changed)


def _expected_event_message(event_type: str) -> dict[str, Any]:
    """Return the exact shared-envelope event shape for an execution decision."""

    return {
        "contentType": "application/cloudevents+json",
        "payload": {
            "schemaFormat": core._SHARED_CONTEXT_SCHEMA_FORMAT,
            "schema": {
                "allOf": [
                    {"$ref": core._SHARED_CONTEXT_ENVELOPE_SCHEMA},
                    {
                        "type": "object",
                        "properties": {"type": {"const": event_type}},
                    },
                ]
            },
        },
    }


def _without_execution_asyncapi(document: dict[str, Any]) -> dict[str, Any]:
    """Return the pre-execution AsyncAPI view for generic contract validation."""

    changed = deepcopy(document)
    channels = changed.get("channels")
    if isinstance(channels, dict):
        channels.pop(_TARGET_STATE_SCHEDULE_CHANNEL_NAME, None)
        channels.pop(_TARGET_STATE_START_CHANNEL_NAME, None)
    operations = changed.get("operations")
    if isinstance(operations, dict):
        operations.pop(_TARGET_STATE_SCHEDULE_OPERATION_NAME, None)
        operations.pop(_TARGET_STATE_START_OPERATION_NAME, None)
    components = changed.get("components")
    if isinstance(components, dict):
        messages = components.get("messages")
        if isinstance(messages, dict):
            messages.pop(_TARGET_STATE_SCHEDULE_MESSAGE_NAME, None)
            messages.pop(_TARGET_STATE_START_MESSAGE_NAME, None)
    return changed


def _validate_execution_event(
    document: dict[str, Any],
    *,
    channel_name: str,
    operation_name: str,
    message_name: str,
    event_type: str,
    command_name: str,
) -> None:
    """Require one execution event to use the shared Context Graph envelope."""

    channels = core._require_mapping(document.get("channels"), "channels")
    operations = core._require_mapping(document.get("operations"), "operations")
    components = core._require_mapping(document.get("components"), "components")
    messages = core._require_mapping(components.get("messages"), "messages")
    channel = core._require_mapping(channels.get(channel_name), channel_name)
    expected_channel = {
        "address": event_type,
        "messages": {
            message_name: {"$ref": f"#/components/messages/{message_name}"}
        },
    }
    if channel != expected_channel:
        raise ContractValidationError(
            f"transformation {command_name} AsyncAPI channel is incomplete"
        )
    operation = core._require_mapping(operations.get(operation_name), operation_name)
    expected_operation = {
        "action": "send",
        "channel": {"$ref": f"#/channels/{channel_name}"},
        "messages": [
            {"$ref": f"#/channels/{channel_name}/messages/{message_name}"}
        ],
    }
    if operation != expected_operation:
        raise ContractValidationError(
            f"transformation {command_name} AsyncAPI operation is incomplete"
        )
    message = core._require_mapping(messages.get(message_name), message_name)
    if message != _expected_event_message(event_type):
        raise ContractValidationError(
            f"transformation {command_name} event must reuse the shared Context Graph envelope"
        )


def validate_asyncapi_document(document: dict[str, Any]) -> int:
    """Validate existing publishers plus schedule and start execution events."""

    legacy_operation_count = core.validate_asyncapi_document(
        _without_execution_asyncapi(document)
    )
    _validate_execution_event(
        document,
        channel_name=_TARGET_STATE_SCHEDULE_CHANNEL_NAME,
        operation_name=_TARGET_STATE_SCHEDULE_OPERATION_NAME,
        message_name=_TARGET_STATE_SCHEDULE_MESSAGE_NAME,
        event_type=_TARGET_STATE_SCHEDULE_EVENT_TYPE,
        command_name="schedule",
    )
    _validate_execution_event(
        document,
        channel_name=_TARGET_STATE_START_CHANNEL_NAME,
        operation_name=_TARGET_STATE_START_OPERATION_NAME,
        message_name=_TARGET_STATE_START_MESSAGE_NAME,
        event_type=_TARGET_STATE_START_EVENT_TYPE,
        command_name="start",
    )
    return legacy_operation_count + 2


def validate_repository(repository_root: Path) -> RepositoryReport:
    """Validate every repository artifact and return the current audit summary."""

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
