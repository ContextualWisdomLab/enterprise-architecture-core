"""Regression coverage for exact schema inventory across ALTER TABLE migrations."""

from pathlib import Path

from ea_core_foundation import validate_migration_sql


def _migration_text(repository_root: Path) -> str:
    """Return production migrations in the exact order used by repository validation."""

    return "\n".join(
        migration_path.read_text(encoding="utf-8")
        for migration_path in sorted(
            (repository_root / "database/migrations").glob("*.sql")
        )
    )


def test_repository_inventory_counts_alter_added_profile_version(
    repository_root: Path,
) -> None:
    """Count ALTER-added columns and live constraints in the logical inventory."""

    counts = validate_migration_sql(_migration_text(repository_root))

    assert counts[1] == 392
    assert counts[3] == 409


def test_alter_add_column_changes_inventory_count(repository_root: Path) -> None:
    """A later ALTER TABLE ADD COLUMN must increase the reported column count."""

    migration_text = _migration_text(repository_root)
    baseline = validate_migration_sql(migration_text)[1]
    extended = validate_migration_sql(
        migration_text
        + "\nALTER TABLE architecture_core.tenant_record "
        + "ADD COLUMN audit_reference text;\n"
    )[1]

    assert extended == baseline + 1


def test_constraint_comment_does_not_change_live_constraint_count(
    repository_root: Path,
) -> None:
    """COMMENT ON CONSTRAINT is documentation, not another schema constraint."""

    migration_text = _migration_text(repository_root)
    baseline = validate_migration_sql(migration_text)[3]
    extended = validate_migration_sql(
        migration_text
        + "\nCOMMENT ON CONSTRAINT tenant_record_primary_key "
        + "ON architecture_core.tenant_record IS 'documented';\n"
    )[3]

    assert extended == baseline
