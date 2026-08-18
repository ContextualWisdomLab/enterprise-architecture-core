"""Database migration validation tests."""

from pathlib import Path

import pytest

from ea_core_foundation import (
    ContractValidationError,
    validate_migration_inventory,
    validate_migration_sql,
)


def test_real_migration_satisfies_foundation_contract(repository_root: Path) -> None:
    """The checked-in migrations satisfy naming and temporal requirements."""

    migration_paths = tuple(
        sorted((repository_root / "database/migrations").glob("*.sql"))
    )
    validate_migration_inventory(migration_paths)
    migration_text = "\n".join(
        migration_path.read_text(encoding="utf-8")
        for migration_path in migration_paths
    )
    counts = validate_migration_sql(migration_text)
    assert counts[0] == 39
    assert counts[1] == 447
    assert counts[2] == 15
    assert counts[3] == 337


def test_migration_column_count_ignores_function_signatures(
    repository_root: Path,
) -> None:
    """Schema inventory counts table columns, not typed function parameters."""

    migration_text = "\n".join(
        migration_path.read_text(encoding="utf-8")
        for migration_path in sorted(
            (repository_root / "database/migrations").glob("*.sql")
        )
    )
    baseline_counts = validate_migration_sql(migration_text)
    function_sql = """
CREATE FUNCTION architecture_core.example_projection(
    requested_record_id uuid
)
RETURNS TABLE (
    result_record_id uuid
)
LANGUAGE sql
AS $$ SELECT requested_record_id $$;
"""
    extended_counts = validate_migration_sql(f"{migration_text}\n{function_sql}")

    assert extended_counts[1] == baseline_counts[1]


def test_migration_inventory_requires_at_least_one_file() -> None:
    """An empty migration directory cannot be treated as a valid sequence."""

    with pytest.raises(ContractValidationError, match="at least one migration"):
        validate_migration_inventory(())


def test_migration_inventory_requires_contiguous_unique_ordinals() -> None:
    """A production migration sequence cannot contain duplicates or gaps."""

    with pytest.raises(ContractValidationError, match="duplicate migration ordinal"):
        validate_migration_inventory(
            (
                Path("0001_identity_objects.sql"),
                Path("0001_duplicate_identity.sql"),
            )
        )

    with pytest.raises(ContractValidationError, match="contiguous"):
        validate_migration_inventory(
            (
                Path("0001_identity_objects.sql"),
                Path("0003_relations_lifecycle.sql"),
            )
        )


def test_migration_inventory_rejects_unversioned_or_noncanonical_names() -> None:
    """Every production SQL file must expose a canonical four-digit ordinal."""

    with pytest.raises(ContractValidationError, match="migration filename"):
        validate_migration_inventory((Path("identity_objects.sql"),))

    with pytest.raises(ContractValidationError, match="migration filename"):
        validate_migration_inventory((Path("0001-Bad.sql"),))


def test_migration_requires_at_least_one_table() -> None:
    """A migration without a table is not a schema foundation."""

    with pytest.raises(ContractValidationError, match="at least one table"):
        validate_migration_sql("SELECT 1;")


@pytest.mark.parametrize(
    ("sql_text", "message"),
    [
        (
            "CREATE TABLE architecture_core.bad (valid_from text, valid_to text, "
            "recorded_at text, superseded_at text, outbox_event text, "
            "tenant_record_id text, truth_status_code text);",
            "table name",
        ),
        (
            "CREATE TABLE bad.good_table (valid_from text, valid_to text, "
            "recorded_at text, superseded_at text, outbox_event text, "
            "tenant_record_id text, truth_status_code text);",
            "schema name",
        ),
        (
            "CREATE TABLE architecture_core.good_table (\n"
            "    bad text,\n"
            "    valid_from text,\n"
            "    valid_to text,\n"
            "    recorded_at text,\n"
            "    superseded_at text,\n"
            "    outbox_event text,\n"
            "    tenant_record_id text,\n"
            "    truth_status_code text\n"
            ");",
            "column name",
        ),
        (
            "CREATE TABLE architecture_core.good_table (valid_from text, "
            "valid_to text, recorded_at text, superseded_at text, "
            "outbox_event text, tenant_record_id text, truth_status_code text); "
            "CREATE INDEX bad ON architecture_core.good_table (valid_from);",
            "index name",
        ),
        (
            "CREATE TABLE architecture_core.good_table (valid_from text, "
            "valid_to text, recorded_at text, superseded_at text, "
            "outbox_event text, tenant_record_id text, truth_status_code text, "
            "CONSTRAINT bad CHECK (true));",
            "constraint name",
        ),
    ],
)
def test_migration_rejects_single_word_database_objects(
    sql_text: str, message: str
) -> None:
    """Schemas, tables, columns, indexes, and constraints use two-word names."""

    with pytest.raises(ContractValidationError, match=message):
        validate_migration_sql(sql_text)


def test_migration_requires_tenant_bound_composite_keys(
    repository_root: Path,
) -> None:
    """Tenant-owned relations and outbox rows cannot cross authority boundaries."""

    migration_text = "\n".join(
        migration_path.read_text(encoding="utf-8")
        for migration_path in sorted(
            (repository_root / "database/migrations").glob("*.sql")
        )
    )
    weakened = migration_text.replace(
        "FOREIGN KEY (tenant_record_id, source_object_id)",
        "FOREIGN KEY (source_object_id)",
    )
    with pytest.raises(ContractValidationError, match="tenant-bound composite keys"):
        validate_migration_sql(weakened)


def test_migration_requires_rls_policy_for_every_tenant_table(
    repository_root: Path,
) -> None:
    """The static gate rejects a tenant table with no matching RLS policy."""

    migration_text = "\n".join(
        migration_path.read_text(encoding="utf-8")
        for migration_path in sorted(
            (repository_root / "database/migrations").glob("*.sql")
        )
    )
    weakened = migration_text.replace(
        "CREATE POLICY tenant_isolation_policy",
        "-- removed tenant isolation policy",
        1,
    )
    with pytest.raises(ContractValidationError, match="tenant isolation policy"):
        validate_migration_sql(weakened)


def test_migration_requires_checksum_ledger(repository_root: Path) -> None:
    """Applied migration identity and content digest must be persisted."""

    migration_text = "\n".join(
        migration_path.read_text(encoding="utf-8")
        for migration_path in sorted(
            (repository_root / "database/migrations").glob("*.sql")
        )
    )
    weakened = migration_text.replace("schema_migration_record", "removed_ledger", 1)
    with pytest.raises(ContractValidationError, match="checksum ledger"):
        validate_migration_sql(weakened)


def test_migration_requires_global_vocabulary_tables(
    repository_root: Path,
) -> None:
    """A clean install cannot omit the shared type and phase vocabularies."""

    migration_text = "\n".join(
        migration_path.read_text(encoding="utf-8")
        for migration_path in sorted(
            (repository_root / "database/migrations").glob("*.sql")
        )
    )
    weakened = migration_text.replace(
        "CREATE TABLE architecture_core.object_type",
        "CREATE TABLE architecture_core.object_kind",
        1,
    )
    with pytest.raises(ContractValidationError, match="required global tables"):
        validate_migration_sql(weakened)


def test_migration_reports_missing_temporal_or_outbox_tokens() -> None:
    """The schema cannot omit required audit and integration primitives."""

    with pytest.raises(ContractValidationError, match="missing required tokens"):
        validate_migration_sql(
            "CREATE TABLE architecture_core.good_table (record_id uuid);"
        )
