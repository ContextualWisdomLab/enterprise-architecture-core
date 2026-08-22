"""Deterministic validation of the repository foundation artifacts."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_OBJECT_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9]*_[a-z0-9_]+$")
_MIGRATION_FILENAME_PATTERN = re.compile(
    r"^(?P<ordinal>[0-9]{4})_[a-z][a-z0-9]*(?:_[a-z0-9]+)*\.sql$"
)
_CREATE_TABLE_PATTERN = re.compile(
    r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?"
    r"(?P<schema>[a-z][a-z0-9_]*)\.(?P<table>[a-z][a-z0-9_]*)",
    re.IGNORECASE,
)
_CREATE_INDEX_PATTERN = re.compile(
    r"CREATE\s+(?:UNIQUE\s+)?INDEX\s+(?:IF\s+NOT\s+EXISTS\s+)?"
    r"(?P<index>[a-z][a-z0-9_]*)",
    re.IGNORECASE,
)
_CREATE_CONSTRAINT_PATTERN = re.compile(
    r"CONSTRAINT\s+(?P<constraint>[a-z][a-z0-9_]*)",
    re.IGNORECASE,
)
_COLUMN_PATTERN = re.compile(
    r"^\s{4}(?P<column>[a-z][a-z0-9_]*)\s+"
    r"(?:uuid|text|integer|boolean|timestamptz|date|numeric|jsonb)\b",
    re.MULTILINE,
)
_GLOBAL_TABLE_NAMES = {
    "schema_migration_record",
    "object_type",
    "relation_type",
    "lifecycle_phase",
}
_SHARED_CONTEXT_ENVELOPE_SCHEMA = (
    "https://schemas.contextualwisdomlab.org/context/"
    "cloudevent-envelope.v1.schema.json"
)
_SHARED_CONTEXT_SCHEMA_FORMAT = "application/schema+json;version=draft-2020-12"
_IMPLEMENTED_RUNTIME_PATHS = {
    "/health": "getHealth",
    "/ready": "getReady",
}
_TARGET_STATE_RUNTIME_PATH = (
    "/v1/technology-target-state-plans/{technology_version_id}"
)
_TARGET_STATE_OPERATION_ID = "getTechnologyTargetStatePlan"
_CWL_TIMESTAMP_SCHEMA = {
    "type": "string",
    "format": "date-time",
    "pattern": (
        r"^[0-9]{4}-[0-9]{2}-[0-9]{2}[Tt]"
        r"(?:[01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9](?:\.[0-9]+)?"
        r"(?:[Zz]|[+-](?:[01][0-9]|2[0-3]):[0-5][0-9])$"
    ),
}
_TARGET_STATE_APPROVAL_RUNTIME_PATH = (
    "/v1/architecture-transformations/{architecture_transformation_id}/approval"
)
_TARGET_STATE_APPROVAL_OPERATION_ID = "approveTechnologyTargetState"
_REQUIRED_CONNECTOR_NAMES = {
    "keyverse_oidc",
    "context_graph_contracts",
    "semantic_data_portal",
    "pg_erd_cloud",
    "lineage_weave",
    "naruon_workspace",
    "github_governance",
}


class ContractValidationError(ValueError):
    """Raised when a foundation artifact violates an accepted contract."""


@dataclass(frozen=True, slots=True)
class RepositoryReport:
    """Summary of successfully validated repository artifacts."""

    table_count: int
    index_count: int
    column_count: int
    constraint_count: int
    openapi_operation_count: int
    asyncapi_operation_count: int
    adr_count: int
    connector_count: int


def _require_mapping(value: Any, field_name: str) -> Mapping[str, Any]:
    """Return a mapping or raise a contract validation error."""

    if not isinstance(value, Mapping):
        raise ContractValidationError(f"{field_name} must be an object")
    return value


def _require_two_word_name(value: str, object_kind: str) -> None:
    """Require a lower-snake identifier with at least two words."""

    if not _OBJECT_NAME_PATTERN.fullmatch(value):
        raise ContractValidationError(
            f"{object_kind} name must contain at least two lower-snake words: {value}"
        )


def validate_migration_inventory(migration_paths: Sequence[Path]) -> None:
    """Require canonical filenames with one contiguous migration ordinal sequence."""

    if not migration_paths:
        raise ContractValidationError("at least one migration is required")
    seen_ordinals: set[int] = set()
    ordinals: list[int] = []
    for migration_path in migration_paths:
        match = _MIGRATION_FILENAME_PATTERN.fullmatch(migration_path.name)
        if match is None:
            raise ContractValidationError(
                f"migration filename is not canonical: {migration_path.name}"
            )
        ordinal = int(match.group("ordinal"))
        if ordinal in seen_ordinals:
            raise ContractValidationError(
                f"duplicate migration ordinal: {ordinal:04d}"
            )
        seen_ordinals.add(ordinal)
        ordinals.append(ordinal)
    expected_ordinals = list(range(1, len(ordinals) + 1))
    if sorted(ordinals) != expected_ordinals:
        raise ContractValidationError(
            "migration ordinals must be contiguous from 0001: "
            f"found {sorted(ordinals)!r}"
        )


def validate_migration_sql(sql_text: str) -> tuple[int, int, int, int]:
    """Validate migration naming and required temporal/outbox primitives."""

    tables = [
        match.group("table").lower()
        for match in _CREATE_TABLE_PATTERN.finditer(sql_text)
    ]
    indexes = [
        match.group("index").lower()
        for match in _CREATE_INDEX_PATTERN.finditer(sql_text)
    ]
    columns = [
        match.group("column").lower()
        for match in _COLUMN_PATTERN.finditer(sql_text)
    ]
    constraints = [
        match.group("constraint").lower()
        for match in _CREATE_CONSTRAINT_PATTERN.finditer(sql_text)
    ]
    if not tables:
        raise ContractValidationError("migration must create at least one table")
    schemas = [
        match.group("schema").lower()
        for match in _CREATE_TABLE_PATTERN.finditer(sql_text)
    ]
    for schema_name in schemas:
        _require_two_word_name(schema_name, "schema")
    for table_name in tables:
        _require_two_word_name(table_name, "table")
    for column_name in columns:
        _require_two_word_name(column_name, "column")
    for index_name in indexes:
        _require_two_word_name(index_name, "index")
    for constraint_name in constraints:
        _require_two_word_name(constraint_name, "constraint")
    required_tokens = {
        "valid_from",
        "valid_to",
        "recorded_at",
        "superseded_at",
        "outbox_event",
        "tenant_record_id",
        "truth_status_code",
        "current_tenant_id",
        "ENABLE ROW LEVEL SECURITY",
        "FORCE ROW LEVEL SECURITY",
    }
    missing_tokens = sorted(token for token in required_tokens if token not in sql_text)
    if missing_tokens:
        raise ContractValidationError(
            f"migration is missing required tokens: {missing_tokens!r}"
        )
    normalized_sql = re.sub(r"\s+", " ", sql_text)
    if (
        "CREATE TABLE architecture_core.schema_migration_record" not in normalized_sql
        or "migration_sha256" not in normalized_sql
    ):
        raise ContractValidationError(
            "migration checksum ledger must persist migration name and SHA-256 digest"
        )
    required_tenant_fragments = {
        "FOREIGN KEY (tenant_record_id, source_object_id)",
        "FOREIGN KEY (tenant_record_id, target_object_id)",
        "FOREIGN KEY (tenant_record_id, aggregate_object_id)",
        "PRIMARY KEY (tenant_record_id, architecture_object_id)",
    }
    missing_fragments = sorted(
        fragment
        for fragment in required_tenant_fragments
        if fragment not in normalized_sql
    )
    if missing_fragments:
        raise ContractValidationError(
            "migration is missing tenant-bound composite keys: "
            f"{missing_fragments!r}"
        )
    missing_global_tables = _GLOBAL_TABLE_NAMES.difference(tables)
    if missing_global_tables:
        raise ContractValidationError(
            "migration is missing required global tables: "
            f"{sorted(missing_global_tables)!r}"
        )
    tenant_table_count = len(tables) - len(_GLOBAL_TABLE_NAMES)
    policy_count = normalized_sql.count("CREATE POLICY tenant_isolation_policy")
    if policy_count != tenant_table_count:
        raise ContractValidationError(
            "every tenant-owned table requires a tenant isolation policy"
        )
    return len(tables), len(columns), len(indexes), len(constraints)


def validate_openapi_document(document: Mapping[str, Any]) -> int:
    """Validate the OpenAPI foundation and return its operation count."""

    if document.get("openapi") != "3.2.0":
        raise ContractValidationError("OpenAPI version must be 3.2.0")
    paths = _require_mapping(document.get("paths"), "paths")
    operation_ids: set[str] = set()
    for path_name, path_item_value in paths.items():
        if not isinstance(path_name, str) or not path_name.startswith("/"):
            raise ContractValidationError("OpenAPI path names must start with /")
        path_item = _require_mapping(path_item_value, f"path {path_name}")
        for method_name, operation_value in path_item.items():
            if method_name not in {"get", "post", "put", "patch", "delete"}:
                continue
            operation = _require_mapping(operation_value, "operation")
            operation_id = operation.get("operationId")
            if not isinstance(operation_id, str) or not operation_id:
                raise ContractValidationError("every operation requires operationId")
            if operation_id in operation_ids:
                raise ContractValidationError(f"duplicate operationId: {operation_id}")
            operation_ids.add(operation_id)
    if not operation_ids:
        raise ContractValidationError("OpenAPI document must define operations")
    security_schemes = _require_mapping(
        _require_mapping(document.get("components"), "components").get(
            "securitySchemes"
        ),
        "securitySchemes",
    )
    if "keyverseBearer" not in security_schemes:
        raise ContractValidationError("Keyverse bearer security scheme is required")
    oidc_contract = _require_mapping(
        document.get("x-keyverse-contract"), "x-keyverse-contract"
    )
    required_checks = oidc_contract.get("requiredChecks")
    if required_checks != [
        "signature",
        "issuer",
        "audience",
        "expiration",
        "tenant",
        "role",
    ]:
        raise ContractValidationError("Keyverse verification checks are incomplete")
    required_configuration = oidc_contract.get("requiredConfiguration")
    if required_configuration != [
        "EA_OIDC_ISSUER",
        "EA_OIDC_AUDIENCE",
        "EA_OIDC_JWKS_URL",
        "EA_TENANT_CLAIM",
        "EA_ROLE_CLAIM",
        "EA_READ_ROLES",
        "EA_APPROVAL_ROLES",
    ]:
        raise ContractValidationError("Keyverse runtime configuration is incomplete")
    return len(operation_ids)


def _require_json_schema_ref(
    operation: Mapping[str, Any],
    path_name: str,
    status_code: str,
    schema_name: str,
) -> None:
    """Require a documented JSON response schema operators can generate against."""

    responses = _require_mapping(
        operation.get("responses"),
        f"{path_name} responses",
    )
    response = _require_mapping(
        responses.get(status_code),
        f"{path_name} {status_code}",
    )
    content = _require_mapping(
        response.get("content"),
        f"{path_name} {status_code} content",
    )
    json_content = _require_mapping(
        content.get("application/json"),
        f"{path_name} {status_code} application/json",
    )
    schema = _require_mapping(
        json_content.get("schema"),
        f"{path_name} {status_code} schema",
    )
    if schema.get("$ref") != f"#/components/schemas/{schema_name}":
        raise ContractValidationError(
            f"{path_name} {status_code} must reference {schema_name}"
        )


def _validate_probe_operations(paths: Mapping[str, Any]) -> None:
    """Require health/readiness probes to stay exact and unauthenticated."""

    for path_name, operation_id in _IMPLEMENTED_RUNTIME_PATHS.items():
        path_item = _require_mapping(paths.get(path_name), f"path {path_name}")
        operation = _require_mapping(path_item.get("get"), f"{path_name} get")
        if operation.get("operationId") != operation_id:
            raise ContractValidationError(
                f"{path_name} operationId must be {operation_id}"
            )
        if operation.get("security") != []:
            raise ContractValidationError(f"{path_name} must remain unauthenticated")
        schema_name = "HealthStatus" if path_name == "/health" else "ReadyStatus"
        _require_json_schema_ref(operation, path_name, "200", schema_name)
        if path_name == "/ready":
            _require_json_schema_ref(operation, path_name, "503", schema_name)


def _parameter_index(operation: Mapping[str, Any]) -> Mapping[tuple[str, str], Any]:
    """Return the exact unique OpenAPI parameter set for one operation."""

    parameters = operation.get("parameters")
    if not isinstance(parameters, Sequence) or isinstance(parameters, (str, bytes)):
        raise ContractValidationError("planner parameters must be an array")
    indexed: dict[tuple[str, str], Any] = {}
    for parameter_value in parameters:
        parameter = _require_mapping(parameter_value, "planner parameter")
        name = parameter.get("name")
        location = parameter.get("in")
        if not isinstance(name, str) or not isinstance(location, str):
            raise ContractValidationError("planner parameter identity is incomplete")
        identity = (name, location)
        if identity in indexed:
            raise ContractValidationError(
                f"duplicate planner parameter: {name} in {location}"
            )
        indexed[identity] = parameter
    return indexed


def _require_parameter(
    parameters: Mapping[tuple[str, str], Any],
    identity: tuple[str, str],
    *,
    required: bool,
    schema: Mapping[str, Any],
) -> None:
    """Require one planner parameter to match its executable parser contract."""

    parameter = _require_mapping(parameters.get(identity), "planner parameter")
    if parameter.get("required") is not required:
        raise ContractValidationError(
            f"planner parameter {identity[0]} has incorrect required state"
        )
    if _require_mapping(parameter.get("schema"), "planner parameter schema") != schema:
        raise ContractValidationError(
            f"planner parameter {identity[0]} has incorrect schema"
        )


def _validate_target_state_operation(paths: Mapping[str, Any]) -> None:
    """Bind the authenticated planner OpenAPI operation to executable behavior."""

    path_item = _require_mapping(
        paths.get(_TARGET_STATE_RUNTIME_PATH),
        f"path {_TARGET_STATE_RUNTIME_PATH}",
    )
    operation = _require_mapping(
        path_item.get("get"),
        f"{_TARGET_STATE_RUNTIME_PATH} get",
    )
    if operation.get("operationId") != _TARGET_STATE_OPERATION_ID:
        raise ContractValidationError(
            "target-state planner operationId must be getTechnologyTargetStatePlan"
        )
    if operation.get("security") != [{"keyverseBearer": []}]:
        raise ContractValidationError(
            "target-state planner must require Keyverse bearer authorization"
        )
    parameters = _parameter_index(operation)
    expected_identities = {
        ("technology_version_id", "path"),
        ("valid_at", "query"),
        ("recorded_at", "query"),
        ("planning_horizon_days", "query"),
    }
    if set(parameters) != expected_identities:
        raise ContractValidationError(
            "target-state planner parameters must match executable request parsing"
        )
    _require_parameter(
        parameters,
        ("technology_version_id", "path"),
        required=True,
        schema={
            "type": "string",
            "format": "uuid",
            "pattern": (
                "^[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-"
                "[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
            ),
        },
    )
    for timestamp_name in ("valid_at", "recorded_at"):
        _require_parameter(
            parameters,
            (timestamp_name, "query"),
            required=True,
            schema=_CWL_TIMESTAMP_SCHEMA,
        )
    _require_parameter(
        parameters,
        ("planning_horizon_days", "query"),
        required=False,
        schema={
            "type": "integer",
            "minimum": 1,
            "maximum": 3650,
            "default": 180,
        },
    )
    _require_json_schema_ref(
        operation,
        _TARGET_STATE_RUNTIME_PATH,
        "200",
        "TargetStatePlanResponse",
    )
    for status_code in ("400", "401", "403", "503"):
        _require_json_schema_ref(
            operation,
            _TARGET_STATE_RUNTIME_PATH,
            status_code,
            "ErrorStatus",
        )


def _validate_target_state_approval_operation(paths: Mapping[str, Any]) -> None:
    """Bind the governed approval OpenAPI operation to executable behavior."""

    path_item = _require_mapping(
        paths.get(_TARGET_STATE_APPROVAL_RUNTIME_PATH),
        f"path {_TARGET_STATE_APPROVAL_RUNTIME_PATH}",
    )
    operation = _require_mapping(
        path_item.get("post"),
        f"{_TARGET_STATE_APPROVAL_RUNTIME_PATH} post",
    )
    if operation.get("operationId") != _TARGET_STATE_APPROVAL_OPERATION_ID:
        raise ContractValidationError(
            "target-state approval operationId must be approveTechnologyTargetState"
        )
    if operation.get("security") != [{"keyverseBearer": []}]:
        raise ContractValidationError(
            "target-state approval must require Keyverse bearer authorization"
        )
    parameters = _parameter_index(operation)
    if set(parameters) != {("architecture_transformation_id", "path")}:
        raise ContractValidationError(
            "target-state approval parameters must match executable request parsing"
        )
    _require_parameter(
        parameters,
        ("architecture_transformation_id", "path"),
        required=True,
        schema={"type": "string", "format": "uuid"},
    )
    expected_request_body = {
        "required": True,
        "content": {
            "application/json": {
                "schema": {"$ref": "#/components/schemas/TargetStateApprovalRequest"}
            }
        },
    }
    if operation.get("requestBody") != expected_request_body:
        raise ContractValidationError(
            "target-state approval request body must match executable JSON parsing"
        )
    for status_code in ("200", "201"):
        _require_json_schema_ref(
            operation,
            _TARGET_STATE_APPROVAL_RUNTIME_PATH,
            status_code,
            "TargetStateApprovalReceipt",
        )
    for status_code in ("400", "401", "403", "503"):
        _require_json_schema_ref(
            operation,
            _TARGET_STATE_APPROVAL_RUNTIME_PATH,
            status_code,
            "ErrorStatus",
        )


def validate_openapi_runtime_surface(document: Mapping[str, Any]) -> None:
    """Require every advertised runtime operation to be executable and exact."""

    paths = _require_mapping(document.get("paths"), "paths")
    expected_paths = {
        *_IMPLEMENTED_RUNTIME_PATHS,
        _TARGET_STATE_RUNTIME_PATH,
        _TARGET_STATE_APPROVAL_RUNTIME_PATH,
    }
    if set(paths) != expected_paths:
        raise ContractValidationError(
            "OpenAPI must advertise only implemented health, ready, planner, "
            "and approval paths"
        )
    _validate_probe_operations(paths)
    _validate_target_state_operation(paths)
    _validate_target_state_approval_operation(paths)
    schemas = _require_mapping(
        _require_mapping(document.get("components"), "components").get("schemas"),
        "schemas",
    )
    required_schemas = {
        "HealthStatus",
        "ReadyStatus",
        "TargetStatePlanResponse",
        "TargetStateDecision",
        "TargetStateApprovalRequest",
        "TargetStateApprovalReceipt",
        "ErrorStatus",
    }
    missing_schemas = required_schemas.difference(schemas)
    if missing_schemas:
        raise ContractValidationError(
            f"missing OpenAPI schemas: {sorted(missing_schemas)!r}"
        )


def validate_connector_catalog(document: Mapping[str, Any]) -> int:
    """Validate the ecosystem connector catalog and return its connector count."""

    if document.get("catalog_version") != "1":
        raise ContractValidationError("connector catalog_version must be 1")
    if "cross-service SQL is prohibited" not in str(document.get("exchange_rule")):
        raise ContractValidationError(
            "connector catalog must prohibit cross-service SQL"
        )
    connectors = document.get("connectors")
    if not isinstance(connectors, Sequence) or isinstance(connectors, (str, bytes)):
        raise ContractValidationError("connectors must be an array")
    seen_names: set[str] = set()
    for connector_value in connectors:
        connector = _require_mapping(connector_value, "connector")
        connector_name = connector.get("connector_name")
        if not isinstance(connector_name, str):
            raise ContractValidationError("connector_name must be a string")
        _require_two_word_name(connector_name, "connector")
        if connector_name in seen_names:
            raise ContractValidationError(f"duplicate connector_name: {connector_name}")
        seen_names.add(connector_name)
        owner_repository = connector.get("owner_repository")
        if not isinstance(owner_repository, str) or not owner_repository:
            raise ContractValidationError("owner_repository is required")
        if connector.get("ea_core_owns") is not False:
            raise ContractValidationError(
                "ecosystem connectors remain outside EA Core ownership"
            )
        next_action = connector.get("next_action")
        if not isinstance(next_action, str) or len(next_action) < 20:
            raise ContractValidationError("each connector requires a next_action")
    missing_connectors = _REQUIRED_CONNECTOR_NAMES.difference(seen_names)
    if missing_connectors:
        raise ContractValidationError(
            "connector catalog is missing required connectors: "
            f"{sorted(missing_connectors)!r}"
        )
    return len(seen_names)


def validate_asyncapi_document(document: Mapping[str, Any]) -> int:
    """Validate the AsyncAPI foundation and return its operation count."""

    if document.get("asyncapi") != "3.1.0":
        raise ContractValidationError("AsyncAPI version must be 3.1.0")
    channels = _require_mapping(document.get("channels"), "channels")
    operations = _require_mapping(document.get("operations"), "operations")
    if not channels or not operations:
        raise ContractValidationError("AsyncAPI requires channels and operations")
    for operation_name, operation_value in operations.items():
        _require_two_word_name(
            re.sub(
                r"([a-z0-9])([A-Z])",
                lambda match: f"{match.group(1)}_{match.group(2)}",
                str(operation_name),
            ).lower(),
            "operation",
        )
        operation = _require_mapping(operation_value, f"operation {operation_name}")
        if operation.get("action") != "send":
            raise ContractValidationError("initial AsyncAPI operations must publish")
    messages = _require_mapping(
        _require_mapping(document.get("components"), "components").get("messages"),
        "messages",
    )
    if not messages:
        raise ContractValidationError("AsyncAPI requires message schemas")
    expected_messages = {
        "ArchitectureObjectChanged": {
            "contentType": "application/cloudevents+json",
            "payload": {
                "schemaFormat": _SHARED_CONTEXT_SCHEMA_FORMAT,
                "schema": {
                    "allOf": [
                        {"$ref": _SHARED_CONTEXT_ENVELOPE_SCHEMA},
                        {
                            "type": "object",
                            "properties": {
                                "type": {
                                    "const": (
                                        "org.contextualwisdomlab.ea.object.changed.v1"
                                    )
                                }
                            },
                        },
                    ]
                },
            },
        },
        "LifecycleChanged": {
            "contentType": "application/cloudevents+json",
            "payload": {
                "schemaFormat": _SHARED_CONTEXT_SCHEMA_FORMAT,
                "schema": {
                    "allOf": [
                        {"$ref": _SHARED_CONTEXT_ENVELOPE_SCHEMA},
                        {
                            "type": "object",
                            "properties": {
                                "type": {
                                    "const": (
                                        "org.contextualwisdomlab.ea.lifecycle.changed.v1"
                                    )
                                }
                            },
                        },
                    ]
                },
            },
        },
        "TransformationApproved": {
            "contentType": "application/cloudevents+json",
            "payload": {
                "schemaFormat": _SHARED_CONTEXT_SCHEMA_FORMAT,
                "schema": {
                    "allOf": [
                        {"$ref": _SHARED_CONTEXT_ENVELOPE_SCHEMA},
                        {
                            "type": "object",
                            "properties": {
                                "type": {
                                    "const": (
                                        "org.contextualwisdomlab.ea.transformation.approved.v1"
                                    )
                                }
                            },
                        },
                    ]
                },
            },
        },
    }
    if messages != expected_messages:
        raise ContractValidationError(
            "EA AsyncAPI messages must reuse the shared Context Graph envelope"
        )
    return len(operations)


def validate_repository(repository_root: Path) -> RepositoryReport:
    """Validate all initial repository artifacts and return a summary."""

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
    (
        table_count,
        column_count,
        index_count,
        constraint_count,
    ) = validate_migration_sql(migration_text)
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
