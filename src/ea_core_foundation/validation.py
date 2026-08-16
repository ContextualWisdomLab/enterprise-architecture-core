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
    tenant_table_count = len(tables) - 3
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
    return len(operation_ids)


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
    return len(operations)


def validate_repository(repository_root: Path) -> RepositoryReport:
    """Validate all initial repository artifacts and return a summary."""

    migration_directory = repository_root / "database/migrations"
    openapi_path = repository_root / "contracts/openapi.json"
    asyncapi_path = repository_root / "contracts/asyncapi.json"
    for required_path in (openapi_path, asyncapi_path):
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
    openapi_operation_count = validate_openapi_document(
        json.loads(openapi_path.read_text(encoding="utf-8"))
    )
    asyncapi_operation_count = validate_asyncapi_document(
        json.loads(asyncapi_path.read_text(encoding="utf-8"))
    )
    adr_count = len(tuple((repository_root / "docs/adr").glob("*.md")))
    if adr_count != 10:
        raise ContractValidationError("the foundation requires exactly ten ADRs")
    return RepositoryReport(
        table_count=table_count,
        column_count=column_count,
        index_count=index_count,
        constraint_count=constraint_count,
        openapi_operation_count=openapi_operation_count,
        asyncapi_operation_count=asyncapi_operation_count,
        adr_count=adr_count,
    )
