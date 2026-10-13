"""Validate the executable Data/AI Context reassessment-status read boundary."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from .. import validation_core as core
from .. import validation_data_management_recheck as base

ContractValidationError = base.ContractValidationError
RepositoryReport = base.RepositoryReport
validate_asyncapi_document = base.validate_asyncapi_document
validate_connector_catalog = base.validate_connector_catalog
validate_migration_inventory = base.validate_migration_inventory
validate_migration_sql = base.validate_migration_sql

_DATA_MANAGEMENT_RECHECK_STATUS_RUNTIME_PATH = (
    "/v1/data-management-assessment-rechecks/"
    "{assessment_recheck_request_id}"
)
_DATA_MANAGEMENT_RECHECK_STATUS_OPERATION_ID = (
    "getDataManagementAssessmentRecheckStatus"
)
_DATA_MANAGEMENT_RECHECK_STATUS_ROLE_CONFIGURATION = (
    "EA_DATA_MANAGEMENT_RECHECK_READ_ROLES"
)
_DATA_MANAGEMENT_RECHECK_STATUS_SCHEMA = "DataManagementAssessmentRecheckStatus"
_CANONICAL_UUID7_SCHEMA = {
    "type": "string",
    "format": "uuid",
    "pattern": (
        "^[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-"
        "[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
    ),
}


def _without_status_role(document: dict[str, Any]) -> dict[str, Any]:
    """Return the command-generation contract without status-read authority."""

    changed = deepcopy(document)
    configuration = changed["x-keyverse-contract"]["requiredConfiguration"]
    if _DATA_MANAGEMENT_RECHECK_STATUS_ROLE_CONFIGURATION not in configuration:
        raise ContractValidationError(
            "x-keyverse-contract requiredConfiguration must include "
            "EA_DATA_MANAGEMENT_RECHECK_READ_ROLES"
        )
    changed["x-keyverse-contract"]["requiredConfiguration"] = [
        value
        for value in configuration
        if value != _DATA_MANAGEMENT_RECHECK_STATUS_ROLE_CONFIGURATION
    ]
    return changed


def validate_openapi_document(document: dict[str, Any]) -> int:
    """Validate OpenAPI plus the purpose-bound reassessment status read role."""

    try:
        changed = _without_status_role(document)
    except (KeyError, TypeError):
        return base.validate_openapi_document(document)
    return base.validate_openapi_document(changed)


def _without_status_openapi(document: dict[str, Any]) -> dict[str, Any]:
    """Return the predecessor runtime view without reassessment-status additions."""

    changed = deepcopy(document)
    changed["paths"].pop(_DATA_MANAGEMENT_RECHECK_STATUS_RUNTIME_PATH, None)
    changed["components"]["schemas"].pop(
        _DATA_MANAGEMENT_RECHECK_STATUS_SCHEMA,
        None,
    )
    return changed


def _validate_status_operation(paths: dict[str, Any]) -> None:
    """Bind the published status route to its strict executable request shape."""

    path_item = core._require_mapping(
        paths.get(_DATA_MANAGEMENT_RECHECK_STATUS_RUNTIME_PATH),
        f"path {_DATA_MANAGEMENT_RECHECK_STATUS_RUNTIME_PATH}",
    )
    operation = core._require_mapping(
        path_item.get("get"),
        f"{_DATA_MANAGEMENT_RECHECK_STATUS_RUNTIME_PATH} get",
    )
    if operation.get("operationId") != _DATA_MANAGEMENT_RECHECK_STATUS_OPERATION_ID:
        raise ContractValidationError(
            "data-management reassessment status operationId must be "
            "getDataManagementAssessmentRecheckStatus"
        )
    if operation.get("security") != [{"keyverseBearer": []}]:
        raise ContractValidationError(
            "data-management reassessment status must require Keyverse bearer "
            "authorization"
        )
    parameters = core._parameter_index(operation)
    parameter_identity = ("assessment_recheck_request_id", "path")
    if set(parameters) != {parameter_identity}:
        raise ContractValidationError(
            "data-management reassessment status parameters must match "
            "executable parsing"
        )
    core._require_parameter(
        parameters,
        parameter_identity,
        required=True,
        schema=_CANONICAL_UUID7_SCHEMA,
    )
    core._require_json_schema_ref(
        operation,
        _DATA_MANAGEMENT_RECHECK_STATUS_RUNTIME_PATH,
        "200",
        _DATA_MANAGEMENT_RECHECK_STATUS_SCHEMA,
    )
    for status_code in ("400", "401", "403", "503"):
        core._require_json_schema_ref(
            operation,
            _DATA_MANAGEMENT_RECHECK_STATUS_RUNTIME_PATH,
            status_code,
            "ErrorStatus",
        )


def validate_openapi_runtime_surface(document: dict[str, Any]) -> None:
    """Require reassessment-status behavior after every predecessor runtime route."""

    try:
        legacy_document = _without_status_openapi(document)
    except (KeyError, TypeError):
        base.validate_openapi_runtime_surface(document)
        return
    base.validate_openapi_runtime_surface(legacy_document)
    paths = core._require_mapping(document.get("paths"), "paths")
    schemas = core._require_mapping(
        core._require_mapping(document.get("components"), "components").get("schemas"),
        "schemas",
    )
    if _DATA_MANAGEMENT_RECHECK_STATUS_SCHEMA not in schemas:
        raise ContractValidationError(
            "missing OpenAPI schema: DataManagementAssessmentRecheckStatus"
        )
    _validate_status_operation(paths)


def validate_repository(repository_root: Path) -> RepositoryReport:
    """Validate repository artifacts with executable reassessment-status contracts."""

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
