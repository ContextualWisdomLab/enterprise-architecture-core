"""Repository-level validation tests."""

import json
import shutil
from pathlib import Path

import pytest

from ea_core_foundation import ContractValidationError, validate_repository
from ea_core_foundation.validation_data_management import (
    validate_repository as validate_data_management_repository,
)
from ea_core_foundation.validation_replan import (
    validate_repository as validate_replan_repository,
)
from scripts.validate_repository import main

_DATA_MANAGEMENT_EVENT_MEMBERS = (
    (
        "dataManagementImprovementEvents",
        "publishDataManagementImprovementInitiativeCreated",
        "DataManagementImprovementInitiativeCreated",
    ),
    (
        "dataManagementEvidenceAcceptedEvents",
        "publishDataManagementEvidenceAccepted",
        "DataManagementEvidenceAccepted",
    ),
    (
        "dataManagementMilestoneCompletedEvents",
        "publishDataManagementMilestoneCompleted",
        "DataManagementMilestoneCompleted",
    ),
    (
        "dataManagementAssessmentRecheckEvents",
        "publishDataManagementAssessmentRecheckRequested",
        "DataManagementAssessmentRecheckRequested",
    ),
)
_DATA_MANAGEMENT_CLOSURE_EVENT_MEMBERS = _DATA_MANAGEMENT_EVENT_MEMBERS[1:]
_DATA_MANAGEMENT_RECHECK_PATH = (
    "/v1/data-management-assessments/"
    "{data_management_assessment_projection_id}/recheck"
)
_DATA_MANAGEMENT_RECHECK_SCHEMAS = (
    "DataManagementAssessmentRecheckRequest",
    "DataManagementAssessmentRecheckReceipt",
)
_DATA_MANAGEMENT_RECHECK_ROLE = "EA_DATA_MANAGEMENT_RECHECK_ROLES"


def _strip_event_contract_members(
    repository_root: Path,
    event_members: tuple[tuple[str, str, str], ...],
) -> None:
    """Remove selected event bindings from a copied repository contract."""

    asyncapi_path = repository_root / "contracts/asyncapi.json"
    document = json.loads(asyncapi_path.read_text(encoding="utf-8"))
    for channel_name, operation_name, message_name in event_members:
        document["channels"].pop(channel_name, None)
        document["operations"].pop(operation_name, None)
        document["components"]["messages"].pop(message_name, None)
    asyncapi_path.write_text(
        json.dumps(document, indent=2) + "\n",
        encoding="utf-8",
    )


def _strip_event_data_contracts(repository_root: Path) -> None:
    """Restore the type-only message generation understood by prior validators."""

    asyncapi_path = repository_root / "contracts/asyncapi.json"
    document = json.loads(asyncapi_path.read_text(encoding="utf-8"))
    for message in document["components"]["messages"].values():
        event_schema = message["payload"]["schema"]["allOf"][1]
        event_schema.pop("required", None)
        event_schema["properties"].pop("data", None)
    asyncapi_path.write_text(
        json.dumps(document, indent=2) + "\n",
        encoding="utf-8",
    )


def _strip_data_management_recheck_openapi_contract(repository_root: Path) -> None:
    """Restore the predecessor OpenAPI generation before compatibility validation."""

    openapi_path = repository_root / "contracts/openapi.json"
    document = json.loads(openapi_path.read_text(encoding="utf-8"))
    document["paths"].pop(_DATA_MANAGEMENT_RECHECK_PATH, None)
    schemas = document["components"]["schemas"]
    for schema_name in _DATA_MANAGEMENT_RECHECK_SCHEMAS:
        schemas.pop(schema_name, None)
    configuration = document["x-keyverse-contract"]["requiredConfiguration"]
    document["x-keyverse-contract"]["requiredConfiguration"] = [
        value for value in configuration if value != _DATA_MANAGEMENT_RECHECK_ROLE
    ]
    openapi_path.write_text(
        json.dumps(document, indent=2) + "\n",
        encoding="utf-8",
    )


def _strip_data_management_event_contract(repository_root: Path) -> None:
    """Restore the previous replanning event view for compatibility validation."""

    _strip_event_contract_members(repository_root, _DATA_MANAGEMENT_EVENT_MEMBERS)
    _strip_event_data_contracts(repository_root)
    _strip_data_management_recheck_openapi_contract(repository_root)


def _strip_data_management_closure_event_contract(repository_root: Path) -> None:
    """Restore the improvement-only event generation for compatibility validation."""

    _strip_event_contract_members(
        repository_root,
        _DATA_MANAGEMENT_CLOSURE_EVENT_MEMBERS,
    )
    _strip_event_data_contracts(repository_root)
    _strip_data_management_recheck_openapi_contract(repository_root)


def test_repository_report_counts_current_artifacts(repository_root: Path) -> None:
    """The complete repository validates and reports the current schema counts."""

    report = validate_repository(repository_root)
    assert report.table_count == 46
    assert report.column_count == 386
    assert report.index_count == 17
    assert report.constraint_count == 407
    assert report.openapi_operation_count == 11
    assert report.asyncapi_operation_count == 12
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


def test_prior_data_management_validator_accepts_its_generation_contract(
    repository_root: Path, tmp_path: Path
) -> None:
    """The improvement validator remains executable against its event generation."""

    target = tmp_path / "data-management-generation"
    shutil.copytree(repository_root, target)
    _strip_data_management_closure_event_contract(target)

    report = validate_data_management_repository(target)

    assert report.asyncapi_operation_count == 9
    assert report.connector_count == 7


def test_prior_data_management_validator_fails_closed_on_missing_contract(
    repository_root: Path, tmp_path: Path
) -> None:
    """The improvement validator still rejects an incomplete repository surface."""

    target = tmp_path / "data-management-missing-contract"
    shutil.copytree(repository_root, target)
    (target / "contracts/asyncapi.json").unlink()

    with pytest.raises(ContractValidationError, match="missing required file"):
        validate_data_management_repository(target)


def test_prior_data_management_validator_requires_decision_evidence(
    repository_root: Path, tmp_path: Path
) -> None:
    """The improvement validator still enforces the minimum ADR evidence baseline."""

    target = tmp_path / "data-management-missing-adrs"
    shutil.copytree(repository_root, target)
    _strip_data_management_closure_event_contract(target)
    for adr_path in (target / "docs/adr").glob("*.md"):
        adr_path.unlink()

    with pytest.raises(ContractValidationError, match="at least ten ADRs"):
        validate_data_management_repository(target)


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
