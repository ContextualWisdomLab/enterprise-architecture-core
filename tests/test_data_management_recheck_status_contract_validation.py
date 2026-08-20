"""Fail-closed contract validation for data-management reassessment status reads."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

import ea_core_foundation.validation_data_management_recheck_status as status_validation

_STATUS_PATH = (
    "/v1/data-management-assessment-rechecks/"
    "{assessment_recheck_request_id}"
)


def test_status_layer_accepts_current_openapi_contract(openapi_document) -> None:
    """The newest validator recognizes all thirteen implemented API operations."""

    assert status_validation.validate_openapi_document(openapi_document) == 14
    status_validation.validate_openapi_runtime_surface(openapi_document)


def test_status_layer_requires_distinct_read_authority(openapi_document) -> None:
    """Status reads cannot silently inherit the reassessment command authority."""

    changed = deepcopy(openapi_document)
    changed["x-keyverse-contract"]["requiredConfiguration"].remove(
        "EA_DATA_MANAGEMENT_RECHECK_READ_ROLES"
    )

    with pytest.raises(
        status_validation.ContractValidationError,
        match="must include EA_DATA_MANAGEMENT_RECHECK_READ_ROLES",
    ):
        status_validation.validate_openapi_document(changed)


def test_status_layer_openapi_fallback_preserves_predecessor_fail_closed_behavior(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Documents without the extension remain the predecessor validator's concern."""

    sentinel_document: dict[str, object] = {}
    monkeypatch.setattr(
        status_validation.base,
        "validate_openapi_document",
        lambda document: 23 if document is sentinel_document else 0,
    )

    assert status_validation.validate_openapi_document(sentinel_document) == 23


def test_status_layer_runtime_fallback_preserves_predecessor_validation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Malformed pre-extension shapes are delegated rather than accepted locally."""

    malformed_document: dict[str, object] = {"paths": []}
    delegated: list[dict[str, object]] = []
    monkeypatch.setattr(
        status_validation.base,
        "validate_openapi_runtime_surface",
        delegated.append,
    )

    status_validation.validate_openapi_runtime_surface(malformed_document)

    assert delegated == [malformed_document]


def test_status_layer_rejects_route_identity_drift(openapi_document) -> None:
    """Generated clients keep one exact reassessment-status operation identity."""

    changed = deepcopy(openapi_document)
    changed["paths"][_STATUS_PATH]["get"]["operationId"] = "getSomeOtherStatus"

    with pytest.raises(
        status_validation.ContractValidationError,
        match="operationId must be getDataManagementAssessmentRecheckStatus",
    ):
        status_validation.validate_openapi_runtime_surface(changed)


def test_status_layer_requires_keyverse_bearer(openapi_document) -> None:
    """The status read cannot become public or inherit ambient transport identity."""

    changed = deepcopy(openapi_document)
    changed["paths"][_STATUS_PATH]["get"]["security"] = []

    with pytest.raises(
        status_validation.ContractValidationError,
        match="must require Keyverse bearer authorization",
    ):
        status_validation.validate_openapi_runtime_surface(changed)


def test_status_layer_requires_exact_uuid7_path_parameter(openapi_document) -> None:
    """The published request identifier remains aligned with executable parsing."""

    changed = deepcopy(openapi_document)
    changed["paths"][_STATUS_PATH]["get"]["parameters"] = []

    with pytest.raises(
        status_validation.ContractValidationError,
        match="parameters must match executable parsing",
    ):
        status_validation.validate_openapi_runtime_surface(changed)


def test_status_layer_requires_status_route(openapi_document) -> None:
    """Removing the buyer read cannot silently collapse to the command generation."""

    changed = deepcopy(openapi_document)
    changed["paths"].pop(_STATUS_PATH)

    with pytest.raises(
        status_validation.ContractValidationError,
        match="must be an object",
    ):
        status_validation.validate_openapi_runtime_surface(changed)


def test_status_layer_requires_response_schema(openapi_document) -> None:
    """A status route without its named response contract must fail closed."""

    changed = deepcopy(openapi_document)
    changed["components"]["schemas"].pop("DataManagementAssessmentRecheckStatus")

    with pytest.raises(
        status_validation.ContractValidationError,
        match="missing OpenAPI schema",
    ):
        status_validation.validate_openapi_runtime_surface(changed)


def _repository_fixture(tmp_path: Path, *, adr_count: int = 10) -> Path:
    """Build the smallest filesystem boundary consumed by repository validation."""

    root = tmp_path / "repository"
    (root / "database/migrations").mkdir(parents=True)
    (root / "contracts/connectors").mkdir(parents=True)
    (root / "docs/adr").mkdir(parents=True)
    (root / "database/migrations/0001_fixture.sql").write_text(
        "-- fixture migration\n",
        encoding="utf-8",
    )
    for relative_path in (
        "contracts/openapi.json",
        "contracts/asyncapi.json",
        "contracts/connectors/ecosystem.json",
    ):
        (root / relative_path).write_text(json.dumps({}), encoding="utf-8")
    for index in range(adr_count):
        (root / f"docs/adr/{index + 1:04d}-fixture.md").write_text(
            "# Accepted fixture decision\n",
            encoding="utf-8",
        )
    return root


def _stub_repository_validators(monkeypatch: pytest.MonkeyPatch) -> None:
    """Isolate orchestration while retaining real filesystem and JSON boundaries."""

    monkeypatch.setattr(
        status_validation,
        "validate_migration_inventory",
        lambda paths: None,
    )
    monkeypatch.setattr(
        status_validation,
        "validate_migration_sql",
        lambda text: (1, 2, 3, 4),
    )
    monkeypatch.setattr(
        status_validation,
        "validate_openapi_document",
        lambda document: 5,
    )
    monkeypatch.setattr(
        status_validation,
        "validate_openapi_runtime_surface",
        lambda document: None,
    )
    monkeypatch.setattr(
        status_validation,
        "validate_asyncapi_document",
        lambda document: 6,
    )
    monkeypatch.setattr(
        status_validation,
        "validate_connector_catalog",
        lambda document: 7,
    )


def test_status_repository_orchestration_retains_all_evidence_dimensions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The newest layer composes database, API, event, connector, and ADR evidence."""

    root = _repository_fixture(tmp_path)
    _stub_repository_validators(monkeypatch)

    report = status_validation.validate_repository(root)

    assert (
        report.table_count,
        report.column_count,
        report.index_count,
        report.constraint_count,
        report.openapi_operation_count,
        report.asyncapi_operation_count,
        report.adr_count,
        report.connector_count,
    ) == (1, 2, 3, 4, 5, 6, 10, 7)


def test_status_repository_orchestration_rejects_missing_contract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Missing contract evidence fails before partial repository validation."""

    root = _repository_fixture(tmp_path)
    _stub_repository_validators(monkeypatch)
    (root / "contracts/asyncapi.json").unlink()

    with pytest.raises(
        status_validation.ContractValidationError,
        match="missing required file",
    ):
        status_validation.validate_repository(root)


def test_status_repository_orchestration_requires_decision_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The newest layer still requires the accepted ADR evidence baseline."""

    root = _repository_fixture(tmp_path, adr_count=9)
    _stub_repository_validators(monkeypatch)

    with pytest.raises(
        status_validation.ContractValidationError,
        match="at least ten ADRs",
    ):
        status_validation.validate_repository(root)
