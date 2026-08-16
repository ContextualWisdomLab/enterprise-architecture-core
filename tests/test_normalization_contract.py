"""Normalization tests for authoritative architecture facts."""

from pathlib import Path


def test_foundation_does_not_duplicate_temporal_or_assessment_facts(
    repository_root: Path,
) -> None:
    """Lifecycle and criticality each have one normalized source of truth."""
    migration_text = "\n".join(
        migration_path.read_text(encoding="utf-8")
        for migration_path in sorted(
            (repository_root / "database/migrations").glob("*.sql")
        )
    )

    assert "lifecycle_status_code" not in migration_text
    assert "business_criticality_code" not in migration_text
