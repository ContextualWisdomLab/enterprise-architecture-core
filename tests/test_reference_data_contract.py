"""Foundation reference-data migration regressions."""

from pathlib import Path


_EXPECTED_OBJECT_TYPES = (
    "business_capability",
    "organization_unit",
    "application_record",
    "application_interface",
    "technology_provider",
    "technology_component",
    "technology_version",
)
_EXPECTED_LIFECYCLE_PHASES = (
    "planned",
    "active",
    "phase_out",
    "end_of_life",
    "retired",
)
_EXPECTED_RELATION_TYPES = (
    "supports_capability",
    "uses_technology",
    "exposes_interface",
    "consumes_interface",
    "provided_by",
    "has_version",
)


def test_foundation_reference_data_is_versioned(repository_root: Path) -> None:
    """A clean install receives usable governed vocabulary without manual SQL."""

    migration_path = (
        repository_root / "database/migrations/0007_foundation_reference_data.sql"
    )
    migration_text = migration_path.read_text(encoding="utf-8")

    assert "INSERT INTO architecture_core.object_type" in migration_text
    assert "INSERT INTO architecture_core.lifecycle_phase" in migration_text
    assert "INSERT INTO architecture_core.relation_type" in migration_text
    for vocabulary_code in (
        *_EXPECTED_OBJECT_TYPES,
        *_EXPECTED_LIFECYCLE_PHASES,
        *_EXPECTED_RELATION_TYPES,
    ):
        assert f"'{vocabulary_code}'" in migration_text


def test_reference_ids_are_explicit_uuidv7_values(repository_root: Path) -> None:
    """Seed identities remain stable across clean installations and projections."""

    migration_text = (
        repository_root / "database/migrations/0007_foundation_reference_data.sql"
    ).read_text(encoding="utf-8")

    assert "DEFAULT" not in migration_text
    assert migration_text.count("0195d145-64e8-7f4f-8a23-a0cc784c") >= 18
