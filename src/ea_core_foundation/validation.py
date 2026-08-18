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


def _without_schedule_role(document: dict[str, Any]) -> dict[str, Any]:
    """Return a legacy-core validation view with the schedule role removed."""

    changed = deepcopy(document)
    configuration = changed["x-keyverse-contract"]["requiredConfiguration"]
    changed["x-keyverse-contract"]["requiredConfiguration"] = [
        value for value in configuration if value != "EA_SCHEDULE_ROLES"
    ]
    return changed


def validate_openapi_document(document: dict[str, Any]) -> int:
    """Validate generic OpenAPI rules plus the schedule-specific role extension."""

    try:
        changed = _without_schedule_role(document)
    except (KeyError, TypeError):
        return core.validate_openapi_document(document)
    return core.validate_openapi_document(changed)


def _validate_target_state_schedule_operation(paths: dict[str, Any]) -> None:
    """Bind the governed scheduling OpenAPI operation to executable behavior."""

    path_item = core._require_mapping(
        paths.get(_TARGET_STATE_SCHEDULE_RUNTIME_PATH),
        f"path {_TARGET_STATE_SCHEDULE_RUNTIME_PATH}",
    )
    operation = core._require_mapping(
        path_item.get("post"),
        f"{_TARGET_STATE_SCHEDULE_RUNTIME_PATH} post",
    )
    if operation.get("operationId") != _TARGET_STATE_SCHEDULE_OPERATION_ID:
        raise ContractValidationError(
            "target-state schedule operationId must be scheduleTechnologyTargetState"
        )
    if operation.get("security") != [{"keyverseBearer": []}]:
        raise ContractValidationError(
            "target-state schedule must require Keyverse bearer authorization"
        )
    parameters = core._parameter_index(operation)
    if set(parameters) != {("architecture_transformation_id", "path")}:
        raise ContractValidationError(
            "target-state schedule parameters must match executable request parsing"
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
                "schema": {"$ref": "#/components/schemas/TargetStateScheduleRequest"}
            }
        },
    }
    if operation.get("requestBody") != expected_request_body:
        raise ContractValidationError(
            "target-state schedule request body must match executable JSON parsing"
        )
    for status_code in ("200", "201"):
        core._require_json_schema_ref(
            operation,
            _TARGET_STATE_SCHEDULE_RUNTIME_PATH,
            status_code,
            "TargetStateScheduleReceipt",
        )
    for status_code in ("400", "401", "403", "503"):
        core._require_json_schema_ref(
            operation,
            _TARGET_STATE_SCHEDULE_RUNTIME_PATH,
            status_code,
            "ErrorStatus",
        )


def validate_openapi_runtime_surface(document: dict[str, Any]) -> None:
    """Require the planner, approval, and schedule surfaces to match runtime code."""

    paths = core._require_mapping(document.get("paths"), "paths")
    _validate_target_state_schedule_operation(paths)
    schemas = core._require_mapping(
        core._require_mapping(document.get("components"), "components").get("schemas"),
        "schemas",
    )
    required_schedule_schemas = {
        "TargetStateScheduleRequest",
        "TargetStateScheduleReceipt",
    }
    missing_schemas = required_schedule_schemas.difference(schemas)
    if missing_schemas:
        raise ContractValidationError(
            f"missing OpenAPI schemas: {sorted(missing_schemas)!r}"
        )
    changed = deepcopy(document)
    changed["paths"].pop(_TARGET_STATE_SCHEDULE_RUNTIME_PATH)
    changed["components"]["schemas"].pop("TargetStateScheduleRequest")
    changed["components"]["schemas"].pop("TargetStateScheduleReceipt")
    core.validate_openapi_runtime_surface(changed)


def _expected_schedule_message() -> dict[str, Any]:
    """Return the exact shared-envelope event shape for a schedule decision."""

    return {
        "contentType": "application/cloudevents+json",
        "payload": {
            "schemaFormat": core._SHARED_CONTEXT_SCHEMA_FORMAT,
            "schema": {
                "allOf": [
                    {"$ref": core._SHARED_CONTEXT_ENVELOPE_SCHEMA},
                    {
                        "type": "object",
                        "properties": {
                            "type": {"const": _TARGET_STATE_SCHEDULE_EVENT_TYPE}
                        },
                    },
                ]
            },
        },
    }


def _without_schedule_asyncapi(document: dict[str, Any]) -> dict[str, Any]:
    """Return the pre-scheduling AsyncAPI view for generic contract validation."""

    changed = deepcopy(document)
    channels = changed.get("channels")
    if isinstance(channels, dict):
        channels.pop(_TARGET_STATE_SCHEDULE_CHANNEL_NAME, None)
    operations = changed.get("operations")
    if isinstance(operations, dict):
        operations.pop(_TARGET_STATE_SCHEDULE_OPERATION_NAME, None)
    components = changed.get("components")
    if isinstance(components, dict):
        messages = components.get("messages")
        if isinstance(messages, dict):
            messages.pop(_TARGET_STATE_SCHEDULE_MESSAGE_NAME, None)
    return changed


def validate_asyncapi_document(document: dict[str, Any]) -> int:
    """Validate existing publishers plus the transformation schedule event."""

    legacy_operation_count = core.validate_asyncapi_document(
        _without_schedule_asyncapi(document)
    )
    channels = core._require_mapping(document.get("channels"), "channels")
    operations = core._require_mapping(document.get("operations"), "operations")
    components = core._require_mapping(document.get("components"), "components")
    messages = core._require_mapping(components.get("messages"), "messages")
    channel = core._require_mapping(
        channels.get(_TARGET_STATE_SCHEDULE_CHANNEL_NAME),
        _TARGET_STATE_SCHEDULE_CHANNEL_NAME,
    )
    expected_channel = {
        "address": _TARGET_STATE_SCHEDULE_EVENT_TYPE,
        "messages": {
            _TARGET_STATE_SCHEDULE_MESSAGE_NAME: {
                "$ref": "#/components/messages/TransformationScheduled"
            }
        },
    }
    if channel != expected_channel:
        raise ContractValidationError(
            "transformation schedule AsyncAPI channel is incomplete"
        )
    operation = core._require_mapping(
        operations.get(_TARGET_STATE_SCHEDULE_OPERATION_NAME),
        _TARGET_STATE_SCHEDULE_OPERATION_NAME,
    )
    expected_operation = {
        "action": "send",
        "channel": {"$ref": "#/channels/transformationScheduleEvents"},
        "messages": [
            {
                "$ref": (
                    "#/channels/transformationScheduleEvents/messages/"
                    "TransformationScheduled"
                )
            }
        ],
    }
    if operation != expected_operation:
        raise ContractValidationError(
            "transformation schedule AsyncAPI operation is incomplete"
        )
    message = core._require_mapping(
        messages.get(_TARGET_STATE_SCHEDULE_MESSAGE_NAME),
        _TARGET_STATE_SCHEDULE_MESSAGE_NAME,
    )
    if message != _expected_schedule_message():
        raise ContractValidationError(
            "transformation schedule event must reuse the shared Context Graph envelope"
        )
    return legacy_operation_count + 1


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
