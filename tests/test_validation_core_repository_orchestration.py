"""Acceptance for the reusable repository-validation orchestration core."""

from __future__ import annotations

from pathlib import Path

import pytest

import ea_core_foundation.validation_core as core


def _fixture_repository(tmp_path: Path, *, adr_count: int = 10) -> Path:
    """Build the smallest realistic repository tree for orchestration tests."""
    root = tmp_path / "repository"
    (root / "database/migrations").mkdir(parents=True)
    (root / "contracts/connectors").mkdir(parents=True)
    (root / "docs/adr").mkdir(parents=True)
    (root / "database/migrations/0001_fixture_foundation.sql").write_text(
        "-- fixture migration\n",
        encoding="utf-8",
    )
    (root / "contracts/openapi.json").write_text("{}", encoding="utf-8")
    (root / "contracts/asyncapi.json").write_text("{}", encoding="utf-8")
    (root / "contracts/connectors/ecosystem.json").write_text("{}", encoding="utf-8")
    for index in range(adr_count):
        (root / f"docs/adr/{index + 1:04d}-fixture-decision.md").write_text(
            "# Accepted fixture decision\n",
            encoding="utf-8",
        )
    return root


def _stub_artifact_validators(monkeypatch) -> None:
    """Keep orchestration tests independent from detailed contract rules."""
    monkeypatch.setattr(core, "validate_migration_inventory", lambda paths: None)
    monkeypatch.setattr(core, "validate_migration_sql", lambda text: (1, 2, 3, 4))
    monkeypatch.setattr(core, "validate_openapi_document", lambda document: 5)
    monkeypatch.setattr(core, "validate_openapi_runtime_surface", lambda document: None)
    monkeypatch.setattr(core, "validate_asyncapi_document", lambda document: 6)
    monkeypatch.setattr(core, "validate_connector_catalog", lambda document: 7)


def test_core_repository_orchestration_reports_all_artifact_dimensions(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Compose migrations, contracts, ADRs, and connectors deterministically."""
    root = _fixture_repository(tmp_path)
    _stub_artifact_validators(monkeypatch)

    report = core.validate_repository(root)

    assert report.table_count == 1
    assert report.column_count == 2
    assert report.index_count == 3
    assert report.constraint_count == 4
    assert report.openapi_operation_count == 5
    assert report.asyncapi_operation_count == 6
    assert report.adr_count == 10
    assert report.connector_count == 7


def test_core_repository_orchestration_rejects_missing_contract_file(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """A missing contract fails before validators see partial repository state."""
    root = _fixture_repository(tmp_path)
    _stub_artifact_validators(monkeypatch)
    (root / "contracts/asyncapi.json").unlink()

    with pytest.raises(core.ContractValidationError, match="missing required file"):
        core.validate_repository(root)


def test_core_repository_orchestration_rejects_adr_baseline_loss(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Repository orchestration preserves accepted-decision evidence."""
    root = _fixture_repository(tmp_path, adr_count=9)
    _stub_artifact_validators(monkeypatch)

    with pytest.raises(core.ContractValidationError, match="at least ten ADRs"):
        core.validate_repository(root)
