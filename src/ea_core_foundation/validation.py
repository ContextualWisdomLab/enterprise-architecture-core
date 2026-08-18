"""Deterministic validation for the complete EA Core contract surface."""

from __future__ import annotations

import json
import re
from collections import Counter
from copy import deepcopy
from pathlib import Path
from typing import Any

from . import validation_core as core

ContractValidationError = core.ContractValidationError
RepositoryReport = core.RepositoryReport
validate_connector_catalog = core.validate_connector_catalog
validate_migration_inventory = core.validate_migration_inventory

_CONSTRAINT_DDL_PATTERN = re.compile(
    r"\b(?:(?P<drop>DROP)\s+CONSTRAINT(?:\s+IF\s+EXISTS)?|"
    r"(?:(?:ADD)\s+)?CONSTRAINT)\s+"
    r"(?P<constraint>[a-z][a-z0-9_]*)",
    re.IGNORECASE,
)
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
_TARGET_STATE_COMPLETE_RUNTIME_PATH = (
    "/v1/architecture-transformations/{architecture_transformation_id}/complete"
)
_TARGET_STATE_COMPLETE_OPERATION_ID = "completeTechnologyTargetState"
_TARGET_STATE_COMPLETE_MESSAGE_NAME = "TransformationCompleted"
_TARGET_STATE_COMPLETE_CHANNEL_NAME = "transformationCompleteEvents"
_TARGET_STATE_COMPLETE_OPERATION_NAME = "publishTransformationCompleted"
_TARGET_STATE_COMPLETE_EVENT_TYPE = (
    "org.contextualwisdomlab.ea.transformation.completed.v1"
)
_TARGET_STATE_VERIFY_RUNTIME_PATH = (
    "/v1/architecture-transformations/{architecture_transformation_id}/verification"
)
_TARGET_STATE_VERIFY_OPERATION_ID = "verifyTechnologyTargetState"
_TARGET_STATE_VERIFY_MESSAGE_NAME = "TransformationVerificationRecorded"
_TARGET_STATE_VERIFY_CHANNEL_NAME = "transformationVerificationEvents"
_TARGET_STATE_VERIFY_OPERATION_NAME = "publishTransformationVerificationRecorded"
_TARGET_STATE_VERIFY_EVENT_TYPE = (
    "org.contextualwisdomlab.ea.transformation.verification_recorded.v1"
)
_EXECUTION_ROLE_CONFIGURATION = frozenset(
    {"EA_SCHEDULE_ROLES", "EA_START_ROLES", "EA_COMPLETE_ROLES", "EA_VERIFY_ROLES"}
)


def _current_constraint_count(sql_text: str) -> int:
    """Count the constraints that remain after ordered DROP/ADD replacement DDL."""

    active_counts: Counter[str] = Counter()
    for match in _CONSTRAINT_DDL_PATTERN.finditer(sql_text):
        constraint_name = match.group("constraint").lower()
        if match.group("drop") is None:
            active_counts[constraint_name] += 1
        else:
            active_counts[constraint_name] = max(
                0,
                active_counts[constraint_name] - 1,
            )
    return sum(active_counts.values())


def validate_migration_sql(sql_text: str) -> tuple[int, int, int, int]:
    """Validate migrations and report current logical schema inventory counts."""

    table_count, column_count, index_count, _ = core.validate_migration_sql(sql_text)
    return (
        table_count,
        column_count,
        index_count,
        _current_constraint_count(sql_text),
    )


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

    path_item = core._require_mapping(paths.get(runtime_path), f"path {runtime_path}")
    operation = core._require_mapping(path_item.get("post"), f"{runtime_path} post")
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
    """Require planner and all governed execution surfaces to match runtime code."""

    paths = core._require_mapping(document.get("paths"), "paths")
    execution_operations = (
        (
            _TARGET_STATE_SCHEDULE_RUNTIME_PATH,
            _TARGET_STATE_SCHEDULE_OPERATION_ID,
            "schedule",
            "TargetStateScheduleRequest",
            "TargetStateScheduleReceipt",
        ),
        (
            _TARGET_STATE_START_RUNTIME_PATH,
            _TARGET_STATE_START_OPERATION_ID,
            "start",
            "TargetStateStartRequest",
            "TargetStateStartReceipt",
        ),
        (
            _TARGET_STATE_COMPLETE_RUNTIME_PATH,
            _TARGET_STATE_COMPLETE_OPERATION_ID,
            "complete",
            "TargetStateCompleteRequest",
            "TargetStateCompleteReceipt",
        ),
        (
            _TARGET_STATE_VERIFY_RUNTIME_PATH,
            _TARGET_STATE_VERIFY_OPERATION_ID,
            "verification",
            "TargetStateVerificationRequest",
            "TargetStateVerificationReceipt",
        ),
    )
    for runtime_path, operation_id, command_name, request_schema, receipt_schema in (
        execution_operations
    ):
        _validate_execution_operation(
            paths,
            runtime_path=runtime_path,
            operation_id=operation_id,
            command_name=command_name,
            request_schema=request_schema,
            receipt_schema=receipt_schema,
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
        "TargetStateCompleteRequest",
        "TargetStateCompleteReceipt",
        "TargetStateVerificationRequest",
        "TargetStateVerificationReceipt",
    }
    missing_schemas = required_execution_schemas.difference(schemas)
    if missing_schemas:
        raise ContractValidationError(
            f"missing OpenAPI schemas: {sorted(missing_schemas)!r}"
        )
    changed = deepcopy(document)
    for runtime_path, *_ in execution_operations:
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
    operations = changed.get("operations")
    components = changed.get("components")
    messages = components.get("messages") if isinstance(components, dict) else None
    for channel_name, operation_name, message_name in (
        (
            _TARGET_STATE_SCHEDULE_CHANNEL_NAME,
            _TARGET_STATE_SCHEDULE_OPERATION_NAME,
            _TARGET_STATE_SCHEDULE_MESSAGE_NAME,
        ),
        (
            _TARGET_STATE_START_CHANNEL_NAME,
            _TARGET_STATE_START_OPERATION_NAME,
            _TARGET_STATE_START_MESSAGE_NAME,
        ),
        (
            _TARGET_STATE_COMPLETE_CHANNEL_NAME,
            _TARGET_STATE_COMPLETE_OPERATION_NAME,
            _TARGET_STATE_COMPLETE_MESSAGE_NAME,
        ),
        (
            _TARGET_STATE_VERIFY_CHANNEL_NAME,
            _TARGET_STATE_VERIFY_OPERATION_NAME,
            _TARGET_STATE_VERIFY_MESSAGE_NAME,
        ),
    ):
        if isinstance(channels, dict):
            channels.pop(channel_name, None)
        if isinstance(operations, dict):
            operations.pop(operation_name, None)
        if isinstance(messages, dict):
            messages.pop(message_name, None)
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
    """Validate existing publishers plus all governed execution decision events."""

    legacy_operation_count = core.validate_asyncapi_document(
        _without_execution_asyncapi(document)
    )
    for channel_name, operation_name, message_name, event_type, command_name in (
        (
            _TARGET_STATE_SCHEDULE_CHANNEL_NAME,
            _TARGET_STATE_SCHEDULE_OPERATION_NAME,
            _TARGET_STATE_SCHEDULE_MESSAGE_NAME,
            _TARGET_STATE_SCHEDULE_EVENT_TYPE,
            "schedule",
        ),
        (
            _TARGET_STATE_START_CHANNEL_NAME,
            _TARGET_STATE_START_OPERATION_NAME,
            _TARGET_STATE_START_MESSAGE_NAME,
            _TARGET_STATE_START_EVENT_TYPE,
            "start",
        ),
        (
            _TARGET_STATE_COMPLETE_CHANNEL_NAME,
            _TARGET_STATE_COMPLETE_OPERATION_NAME,
            _TARGET_STATE_COMPLETE_MESSAGE_NAME,
            _TARGET_STATE_COMPLETE_EVENT_TYPE,
            "complete",
        ),
        (
            _TARGET_STATE_VERIFY_CHANNEL_NAME,
            _TARGET_STATE_VERIFY_OPERATION_NAME,
            _TARGET_STATE_VERIFY_MESSAGE_NAME,
            _TARGET_STATE_VERIFY_EVENT_TYPE,
            "verification",
        ),
    ):
        _validate_execution_event(
            document,
            channel_name=channel_name,
            operation_name=operation_name,
            message_name=message_name,
            event_type=event_type,
            command_name=command_name,
        )
    return legacy_operation_count + 4


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
