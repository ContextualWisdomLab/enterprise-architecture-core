"""Bounded-context ownership regressions for historical foundation paths."""

import ast
import importlib
from pathlib import Path


def _assert_behavior_free_compatibility_facade(
    *,
    owner_path: Path,
    compatibility_path: Path,
    owner_module: str,
) -> None:
    """Require one historical module to delegate behavior to its bounded context."""

    assert owner_path.is_file()
    compatibility_tree = ast.parse(
        compatibility_path.read_text(encoding="utf-8"),
        filename=str(compatibility_path),
    )
    behavior_nodes = (
        ast.ClassDef,
        ast.FunctionDef,
        ast.AsyncFunctionDef,
        ast.If,
        ast.For,
        ast.While,
        ast.Try,
        ast.With,
    )
    assert not any(
        isinstance(node, behavior_nodes) for node in ast.walk(compatibility_tree)
    )
    assert any(
        isinstance(node, ast.ImportFrom)
        and node.level == 1
        and node.module == owner_module
        for node in compatibility_tree.body
    )


def test_connector_validation_has_cross_domain_evidence_owner_path() -> None:
    """Keep connector contract behavior out of the historical foundation bucket."""

    _assert_behavior_free_compatibility_facade(
        owner_path=Path(
            "src/ea_core_foundation/cross_domain_evidence/connector_catalog.py"
        ),
        compatibility_path=Path(
            "src/ea_core_foundation/validation_connector_catalog.py"
        ),
        owner_module="cross_domain_evidence.connector_catalog",
    )


def test_legacy_connector_validation_import_is_only_a_compatibility_alias() -> None:
    """Preserve the public validator while moving behavior to its bounded context."""

    compatibility = importlib.import_module(
        "ea_core_foundation.validation_connector_catalog"
    )
    owner = importlib.import_module(
        "ea_core_foundation.cross_domain_evidence.connector_catalog"
    )
    assert compatibility.validate_connector_catalog is owner.validate_connector_catalog
    assert compatibility.validate_repository is owner.validate_repository
    assert compatibility.ContractValidationError is owner.ContractValidationError
    assert compatibility.RepositoryReport is owner.RepositoryReport


def test_reassessment_status_validation_has_cross_domain_evidence_owner_path() -> None:
    """Keep foreign-evidence reassessment validation in its supporting context."""

    _assert_behavior_free_compatibility_facade(
        owner_path=Path(
            "src/ea_core_foundation/cross_domain_evidence/"
            "data_management_recheck_status.py"
        ),
        compatibility_path=Path(
            "src/ea_core_foundation/validation_data_management_recheck_status.py"
        ),
        owner_module="cross_domain_evidence.data_management_recheck_status",
    )


def test_legacy_reassessment_status_validation_is_a_compatibility_alias() -> None:
    """Preserve validator identity while moving behavior to its bounded context."""

    compatibility = importlib.import_module(
        "ea_core_foundation.validation_data_management_recheck_status"
    )
    owner = importlib.import_module(
        "ea_core_foundation.cross_domain_evidence.data_management_recheck_status"
    )
    public_names = (
        "ContractValidationError",
        "RepositoryReport",
        "validate_asyncapi_document",
        "validate_connector_catalog",
        "validate_migration_inventory",
        "validate_migration_sql",
        "validate_openapi_document",
        "validate_openapi_runtime_surface",
        "validate_repository",
    )
    for name in public_names:
        assert getattr(compatibility, name) is getattr(owner, name)


def test_reassessment_status_runtime_has_portfolio_assessment_owner_path() -> None:
    """Keep EA-owned reassessment follow-up in the Portfolio Assessment context."""

    _assert_behavior_free_compatibility_facade(
        owner_path=Path(
            "src/ea_core_foundation/portfolio_assessment/"
            "data_management_recheck_status.py"
        ),
        compatibility_path=Path(
            "src/ea_core_foundation/data_management_recheck_status.py"
        ),
        owner_module="portfolio_assessment.data_management_recheck_status",
    )


def test_legacy_reassessment_status_runtime_is_a_compatibility_alias() -> None:
    """Preserve the runtime import while moving behavior to Portfolio Assessment."""

    compatibility = importlib.import_module(
        "ea_core_foundation.data_management_recheck_status"
    )
    owner = importlib.import_module(
        "ea_core_foundation.portfolio_assessment.data_management_recheck_status"
    )
    public_names = (
        "DataManagementRecheckStatusRequest",
        "build_data_management_recheck_status_authorization_config",
        "build_data_management_recheck_status_reader",
        "parse_data_management_recheck_status_request",
    )
    for name in public_names:
        assert getattr(compatibility, name) is getattr(owner, name)
