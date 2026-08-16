"""Normalization tests for authoritative architecture facts."""

from pathlib import Path


def _migration_corpus(repository_root: Path) -> str:
    """Return production migrations in deterministic order."""

    return "\n".join(
        migration_path.read_text(encoding="utf-8")
        for migration_path in sorted(
            (repository_root / "database/migrations").glob("*.sql")
        )
    )


def test_foundation_does_not_duplicate_temporal_or_assessment_facts(
    repository_root: Path,
) -> None:
    """Lifecycle and criticality each have one normalized source of truth."""

    migration_text = _migration_corpus(repository_root)

    assert "lifecycle_status_code" not in migration_text
    assert "business_criticality_code" not in migration_text


def test_canonical_asset_uri_is_a_projection_not_stored_fact(
    repository_root: Path,
) -> None:
    """Canonical references derive from normalized identity determinants."""

    migration_text = _migration_corpus(repository_root)

    assert "canonical_asset_uri text" not in migration_text
    assert (
        "CREATE VIEW architecture_core.architecture_object_reference" in migration_text
    )
    assert "AS canonical_asset_uri" in migration_text
    assert "tenant_record.tenant_code" in migration_text
    assert "object_type.object_type_code" in migration_text
