"""Repository-level validation tests."""

import shutil
from pathlib import Path

import pytest

from ea_core_foundation import ContractValidationError, validate_repository
from scripts.validate_repository import main


def test_repository_report_counts_foundation_artifacts(repository_root: Path) -> None:
    """The complete repository validates and reports stable minimum counts."""

    report = validate_repository(repository_root)
    assert report.table_count == 19
    assert report.column_count == 123
    assert report.index_count == 7
    assert report.constraint_count == 121
    assert report.openapi_operation_count == 7
    assert report.asyncapi_operation_count == 2
    assert report.adr_count == 10


def test_repository_validation_reports_missing_required_file(
    repository_root: Path, tmp_path: Path
) -> None:
    """A missing contract or migration fails before partial validation."""

    target = tmp_path / "repository"
    shutil.copytree(repository_root, target)
    (target / "contracts/openapi.json").unlink()
    with pytest.raises(ContractValidationError, match="missing required file"):
        validate_repository(target)


def test_repository_validation_requires_at_least_one_migration(
    repository_root: Path, tmp_path: Path
) -> None:
    """An empty migration directory fails before contract validation."""

    target = tmp_path / "repository"
    shutil.copytree(repository_root, target)
    for migration_path in (target / "database/migrations").glob("*.sql"):
        migration_path.unlink()
    with pytest.raises(ContractValidationError, match="missing required migrations"):
        validate_repository(target)


def test_repository_validation_requires_exact_adr_baseline(
    repository_root: Path, tmp_path: Path
) -> None:
    """The initial decision baseline cannot silently lose an ADR."""

    target = tmp_path / "repository"
    shutil.copytree(repository_root, target)
    next((target / "docs/adr").glob("*.md")).unlink()
    with pytest.raises(ContractValidationError, match="exactly ten ADRs"):
        validate_repository(target)


def test_validation_script_prints_summary(capsys) -> None:
    """The command-line entry point returns success and an audit summary."""

    assert main() == 0
    output = capsys.readouterr().out
    assert "validated" in output
    assert "10 ADRs" in output
