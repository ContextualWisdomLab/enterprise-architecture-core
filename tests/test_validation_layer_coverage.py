"""Fail-closed coverage for layered Context Fabric contract validation."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

import ea_core_foundation.validation_data_management_closure as closure_validation
import ea_core_foundation.validation_data_management_recheck as recheck_validation
import ea_core_foundation.validation_replan as replan_validation

_RECHECK_PATH = (
    "/v1/data-management-assessments/"
    "{data_management_assessment_projection_id}/recheck"
)


def _repository_fixture(tmp_path: Path, *, adr_count: int = 10) -> Path:
    """Build the smallest real filesystem boundary consumed by a layer validator."""

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
    (root / "contracts/connectors/ecosystem.json").write_text(
        "{}",
        encoding="utf-8",
    )
    for index in range(adr_count):
        (root / f"docs/adr/{index + 1:04d}-fixture.md").write_text(
            "# Accepted fixture decision\n",
            encoding="utf-8",
        )
    return root


def _stub_closure_artifact_validators(monkeypatch: pytest.MonkeyPatch) -> None:
    """Isolate repository orchestration while retaining real filesystem evidence."""

    monkeypatch.setattr(
        closure_validation,
        "validate_migration_inventory",
        lambda paths: None,
    )
    monkeypatch.setattr(
        closure_validation,
        "validate_migration_sql",
        lambda text: (1, 2, 3, 4),
    )
    monkeypatch.setattr(
        closure_validation,
        "validate_openapi_document",
        lambda document: 5,
    )
    monkeypatch.setattr(
        closure_validation,
        "validate_openapi_runtime_surface",
        lambda document: None,
    )
    monkeypatch.setattr(
        closure_validation,
        "validate_asyncapi_document",
        lambda document: 6,
    )
    monkeypatch.setattr(
        closure_validation,
        "validate_connector_catalog",
        lambda document: 7,
    )


def test_closure_repository_orchestration_retains_all_evidence_dimensions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The retained evidence-closure layer still composes every artifact dimension."""

    root = _repository_fixture(tmp_path)
    _stub_closure_artifact_validators(monkeypatch)

    report = closure_validation.validate_repository(root)

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


def test_closure_repository_orchestration_rejects_missing_contract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reject a retained validation layer when required contract evidence is absent."""

    root = _repository_fixture(tmp_path)
    _stub_closure_artifact_validators(monkeypatch)
    (root / "contracts/asyncapi.json").unlink()

    with pytest.raises(
        closure_validation.ContractValidationError,
        match="missing required file",
    ):
        closure_validation.validate_repository(root)


def test_closure_repository_orchestration_requires_decision_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Repository validation rejects an incomplete accepted-ADR evidence set."""

    root = _repository_fixture(tmp_path, adr_count=9)
    _stub_closure_artifact_validators(monkeypatch)

    with pytest.raises(
        closure_validation.ContractValidationError,
        match="at least ten ADRs",
    ):
        closure_validation.validate_repository(root)


def test_replan_role_removal_rejects_missing_replan_authority(
    openapi_document: dict[str, object],
) -> None:
    """A list-shaped Keyverse contract cannot silently omit replanning authority."""

    changed = deepcopy(openapi_document)
    changed["x-keyverse-contract"]["requiredConfiguration"].remove("EA_REPLAN_ROLES")

    with pytest.raises(
        replan_validation.ContractValidationError,
        match="must include EA_REPLAN_ROLES",
    ):
        replan_validation._without_replan_role(changed)


def test_recheck_openapi_legacy_fallback_delegates_on_missing_extension(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A missing reassessment extension is delegated to the preceding validator."""

    sentinel_document: dict[str, object] = {}
    monkeypatch.setattr(
        recheck_validation.base,
        "validate_openapi_document",
        lambda document: 23 if document is sentinel_document else 0,
    )

    assert recheck_validation.validate_openapi_document(sentinel_document) == 23


def test_recheck_runtime_legacy_fallback_delegates_on_malformed_shape(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Malformed reassessment additions are still judged by the preceding boundary."""

    malformed_document: dict[str, object] = {"paths": []}
    delegated: list[dict[str, object]] = []
    monkeypatch.setattr(
        recheck_validation.base,
        "validate_openapi_runtime_surface",
        delegated.append,
    )

    recheck_validation.validate_openapi_runtime_surface(malformed_document)

    assert delegated == [malformed_document]


def test_recheck_role_is_mandatory_when_keyverse_configuration_is_present(
    openapi_document: dict[str, object],
) -> None:
    """The reassessment operation cannot inherit a different purpose-bound role."""

    changed = deepcopy(openapi_document)
    changed["x-keyverse-contract"]["requiredConfiguration"].remove(
        "EA_DATA_MANAGEMENT_RECHECK_ROLES"
    )

    with pytest.raises(
        recheck_validation.ContractValidationError,
        match="must include EA_DATA_MANAGEMENT_RECHECK_ROLES",
    ):
        recheck_validation.validate_openapi_document(changed)


@pytest.mark.parametrize(
    ("field_name", "invalid_value", "message"),
    [
        (
            "operationId",
            "requestSomeOtherAssessment",
            "operationId must be requestDataManagementAssessmentRecheck",
        ),
        (
            "security",
            [],
            "must require Keyverse bearer authorization",
        ),
        (
            "parameters",
            [],
            "parameters must match executable parsing",
        ),
        (
            "requestBody",
            {},
            "request body must match executable parsing",
        ),
    ],
)
def test_recheck_operation_fails_closed_when_published_boundary_drifts(
    openapi_document: dict[str, object],
    field_name: str,
    invalid_value: object,
    message: str,
) -> None:
    """Published reassessment metadata must remain identical to executable parsing."""

    changed = deepcopy(openapi_document)
    changed["paths"][_RECHECK_PATH]["post"][field_name] = invalid_value

    with pytest.raises(recheck_validation.ContractValidationError, match=message):
        recheck_validation.validate_openapi_runtime_surface(changed)


def test_recheck_runtime_requires_both_reassessment_schemas(
    openapi_document: dict[str, object],
) -> None:
    """Request and receipt schemas are inseparable from the reassessment command."""

    for schema_name in (
        "DataManagementAssessmentRecheckRequest",
        "DataManagementAssessmentRecheckReceipt",
    ):
        changed = deepcopy(openapi_document)
        changed["components"]["schemas"].pop(schema_name)
        with pytest.raises(
            recheck_validation.ContractValidationError,
            match="missing OpenAPI schemas",
        ):
            recheck_validation.validate_openapi_runtime_surface(changed)
