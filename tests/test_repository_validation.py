"""Repository-level validation tests."""

import json
import shutil
from pathlib import Path

import pytest

from ea_core_foundation import ContractValidationError, validate_repository
from ea_core_foundation.validation_replan import (
    validate_repository as validate_replan_repository,
)
from scripts.validate_repository import main


def _strip_data_management_event_contract(repository_root: Path) -> None:
    """Restore the previous replanning event view for compatibility validation."""

    asyncapi_path = repository_root / "contracts/asyncapi.json"
    document = json.loads(asyncapi_path.read_text(encoding="utf-8"))
    document["channels"].pop("dataManagementImprovementEvents")
    document["operations"].pop("publishDataManagementImprovementInitiativeCreated")
    document["components"]["messages"].pop("DataManagementImprovementInitiativeCreated")
    asyncapi_path.write_text(
        json.dumps(document, indent=2) + "\n",
        encoding="utf-8",
    )


def test_repository_report_counts_current_artifacts(repository_root: Path) -> None:
    """The complete repository validates and reports the current schema counts."""

    report = validate_repository(repository_root)
    assert report.table_count == 43
    assert report.column_count == 364
    assert report.index_count == 17
    assert report.constraint_count == 385
    assert report.openapi_operation_count == 10
    assert report.asyncapi_operation_count == 9
    assert report.adr_count >= 19
    assert report.connector_count == 7


def test_repository_validation_reports_missing_required_file(
    repository_root: Path, tmp_path: Path
) -> None:
    """A missing contract or migration fails before partial validation."""

    target = tmp_path / "repository"
    shutil.copytree(repository_root, target)
    (target / "contracts/openapi.json").unlink()
    with pytest.raises(ContractValidationError, match="missing required file"):
        validate_repository(target)
    (target / "contracts/openapi.json").write_text("{}", encoding="utf-8")
    (target / "contracts/connectors/ecosystem.json").unlink()
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
    with pytest.raises(ContractValidationError, match="at least one migration"):
        validate_repository(target)


def test_repository_validation_requires_exact_adr_baseline(
    repository_root: Path, tmp_path: Path
) -> None:
    """The accepted decision baseline cannot silently lose all ADR evidence."""

    target = tmp_path / "repository"
    shutil.copytree(repository_root, target)
    for adr_path in (target / "docs/adr").glob("*.md"):
        adr_path.unlink()
    with pytest.raises(ContractValidationError, match="at least ten ADRs"):
        validate_repository(target)


def test_prior_replan_validator_accepts_its_generation_contract(
    repository_root: Path, tmp_path: Path
) -> None:
    """The preceding validator remains executable against its event generation."""

    target = tmp_path / "replan-generation"
    shutil.copytree(repository_root, target)
    _strip_data_management_event_contract(target)

    report = validate_replan_repository(target)

    assert report.asyncapi_operation_count == 8
    assert report.connector_count == 7


def test_prior_replan_validator_fails_closed_on_missing_contract(
    repository_root: Path, tmp_path: Path
) -> None:
    """The preceding validator still rejects an incomplete repository surface."""

    target = tmp_path / "replan-missing-contract"
    shutil.copytree(repository_root, target)
    (target / "contracts/asyncapi.json").unlink()

    with pytest.raises(ContractValidationError, match="missing required file"):
        validate_replan_repository(target)


def test_prior_replan_validator_requires_decision_evidence(
    repository_root: Path, tmp_path: Path
) -> None:
    """The preceding validator still enforces the minimum ADR evidence baseline."""

    target = tmp_path / "replan-missing-adrs"
    shutil.copytree(repository_root, target)
    _strip_data_management_event_contract(target)
    for adr_path in (target / "docs/adr").glob("*.md"):
        adr_path.unlink()

    with pytest.raises(ContractValidationError, match="at least ten ADRs"):
        validate_replan_repository(target)


def test_validation_script_prints_summary(capsys) -> None:
    """The command-line entry point returns success and an audit summary."""

    assert main() == 0
    output = capsys.readouterr().out
    assert "validated" in output
    assert "ADRs" in output
    assert "connectors" in output
