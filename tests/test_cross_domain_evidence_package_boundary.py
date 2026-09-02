"""Cross-Domain Evidence package ownership regressions."""

import ast
import importlib
from pathlib import Path


def test_connector_validation_has_cross_domain_evidence_owner_path() -> None:
    """Keep connector contract behavior out of the historical foundation bucket."""

    owner_path = Path(
        "src/ea_core_foundation/cross_domain_evidence/connector_catalog.py"
    )
    compatibility_path = Path(
        "src/ea_core_foundation/validation_connector_catalog.py"
    )
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
        and node.module == "cross_domain_evidence.connector_catalog"
        for node in compatibility_tree.body
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
