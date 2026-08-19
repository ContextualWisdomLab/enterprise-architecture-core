"""Validation extension for the executable data-management reassessment command."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from . import validation_core as core
from . import validation_data_management_closure as base

ContractValidationError = base.ContractValidationError
RepositoryReport = base.RepositoryReport
validate_asyncapi_document = base.validate_asyncapi_document
validate_connector_catalog = base.validate_connector_catalog
validate_migration_inventory = base.validate_migration_inventory
validate_migration_sql = base.validate_migration_sql

_DATA_MANAGEMENT_RECHECK_RUNTIME_PATH = (
    "/v1/data-management-assessments/"
    "{data_management_assessment_projection_id}/recheck"
)
_DATA_MANAGEMENT_RECHECK_OPERATION_ID = "requestDataManagementAssessmentRecheck"
_DATA_MANAGEMENT_RECHECK_ROLE_CONFIGURATION = "EA_DATA_MANAGEMENT_RECHECK_ROLES"
_DATA_MANAGEMENT_RECHECK_REQUEST_SCHEMA = "DataManagementAssessmentRecheckRequest"
_DATA_MANAGEMENT_RECHECK_RECEIPT_SCHEMA = "DataManagementAssessmentRecheckReceipt"
_CANONICAL_UUID7_SCHEMA = {
    "type": "string",
    "format": "uuid",
    "pattern": (
        "^[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-"
        "[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
    ),
}


def _without_recheck_role(document: dict[str, Any]) -> dict[str, Any]:
    """Return the evidence-closure contract view without reassessment authority."""

    changed = deepcopy(document)
    configuration = changed["x-keyverse-contract"]["requiredConfiguration"]
    if _DATA_MANAGEMENT_RECHECK_ROLE_CONFIGURATION not in configuration:
        raise ContractValidationError(
            "x-keyverse-contract requiredConfiguration must include "
            "EA_DATA_MANAGEMENT_RECHECK_ROLES"
        )
    changed["x-keyverse-contract"]["requiredConfiguration"] = [
        value
        for value in configuration
        if value != _DATA_MANAGEMENT_RECHECK_ROLE_CONFIGURATION
    ]
    return changed


def validate_openapi_document(document: dict[str, Any]) -> int:
    """Validate OpenAPI plus the distinct reassessment authorization role."""

    try:
        changed = _without_recheck_role(document)
    except (KeyError, TypeError):
        return base.validate_openapi_document(document)
    return base.validate_openapi_document(changed)


def _without_recheck_openapi(document: dict[str, Any]) -> dict[str, Any]:
    """Return the evidence-closure runtime view without reassessment additions."""

    changed = deepcopy(document)
    changed["paths"].pop(_DATA_MANAGEMENT_RECHECK_RUNTIME_PATH, None)
    schemas = changed["components"]["schemas"]
    schemas.pop(_DATA_MANAGEMENT_RECHECK_REQUEST_SCHEMA, None)
    schemas.pop(_DATA_MANAGEMENT_RECHECK_RECEIPT_SCHEMA, None)
    return changed


def _validate_recheck_operation(paths: dict[str, Any]) -> None:
    """Bind the published reassessment route to its strict executable parser."""

    path_item = core._require_mapping(
        paths.get(_DATA_MANAGEMENT_RECHECK_RUNTIME_PATH),
        f"path {_DATA_MANAGEMENT_RECHECK_RUNTIME_PATH}",
    )
    operation = core._require_mapping(
        path_item.get("post"),
        f"{_DATA_MANAGEMENT_RECHECK_RUNTIME_PATH} post",
    )
    if operation.get("operationId") != _DATA_MANAGEMENT_RECHECK_OPERATION_ID:
        raise ContractValidationError(
            "data-management reassessment operationId must be "
            "requestDataManagementAssessmentRecheck"
        )
    if operation.get("security") != [{"keyverseBearer": []}]:
        raise ContractValidationError(
            "data-management reassessment must require Keyverse bearer authorization"
        )
    parameters = core._parameter_index(operation)
    parameter_identity = ("data_management_assessment_projection_id", "path")
    if set(parameters) != {parameter_identity}:
        raise ContractValidationError(
            "data-management reassessment parameters must match executable parsing"
        )
    core._require_parameter(
        parameters,
        parameter_identity,
        required=True,
        schema=_CANONICAL_UUID7_SCHEMA,
    )
    expected_request_body = {
        "required": True,
        "content": {
            "application/json": {
                "schema": {
                    "$ref": (
                        "#/components/schemas/"
                        f"{_DATA_MANAGEMENT_RECHECK_REQUEST_SCHEMA}"
                    )
                }
            }
        },
    }
    if operation.get("requestBody") != expected_request_body:
        raise ContractValidationError(
            "data-management reassessment request body must match executable parsing"
        )
    core._require_json_schema_ref(
        operation,
        _DATA_MANAGEMENT_RECHECK_RUNTIME_PATH,
        "200",
        _DATA_MANAGEMENT_RECHECK_RECEIPT_SCHEMA,
    )
    for status_code in ("400", "401", "403", "503"):
        core._require_json_schema_ref(
            operation,
            _DATA_MANAGEMENT_RECHECK_RUNTIME_PATH,
            status_code,
            "ErrorStatus",
        )


def validate_openapi_runtime_surface(document: dict[str, Any]) -> None:
    """Require reassessment behavior in addition to every preceding runtime route."""

    try:
        legacy_document = _without_recheck_openapi(document)
    except (KeyError, TypeError):
        base.validate_openapi_runtime_surface(document)
        return
    base.validate_openapi_runtime_surface(legacy_document)
    paths = core._require_mapping(document.get("paths"), "paths")
    schemas = core._require_mapping(
        core._require_mapping(document.get("components"), "components").get("schemas"),
        "schemas",
    )
    missing_schemas = {
        _DATA_MANAGEMENT_RECHECK_REQUEST_SCHEMA,
        _DATA_MANAGEMENT_RECHECK_RECEIPT_SCHEMA,
    }.difference(schemas)
    if missing_schemas:
        raise ContractValidationError(
            f"missing OpenAPI schemas: {sorted(missing_schemas)!r}"
        )
    _validate_recheck_operation(paths)


def validate_repository(repository_root: Path) -> RepositoryReport:
    """Validate repository artifacts with executable reassessment contracts."""

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
