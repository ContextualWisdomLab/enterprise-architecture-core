"""Portfolio Assessment bounded-context ownership regressions."""

import ast
import importlib
from pathlib import Path


def test_portfolio_read_model_has_bounded_context_owner_path() -> None:
    """Keep portfolio assessment read behavior out of the foundation root."""

    owner_path = Path(
        "src/ea_core_foundation/portfolio_assessment/portfolio_assessment.py"
    )
    compatibility_path = Path("src/ea_core_foundation/portfolio.py")
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
        and node.module == "portfolio_assessment.portfolio_assessment"
        for node in compatibility_tree.body
    )


def test_legacy_portfolio_read_model_is_a_compatibility_alias() -> None:
    """Preserve the public portfolio read API while moving its behavior."""

    compatibility = importlib.import_module("ea_core_foundation.portfolio")
    owner = importlib.import_module(
        "ea_core_foundation.portfolio_assessment.portfolio_assessment"
    )
    public_names = (
        "PortfolioAssessmentRequest",
        "build_portfolio_assessment_authorization_config",
        "build_portfolio_assessment_reader",
        "build_portfolio_assessment_summary_authorization_config",
        "build_portfolio_assessment_summary_reader",
        "parse_portfolio_assessment_request",
        "parse_portfolio_assessment_summary_request",
        "summarize_portfolio_assessments",
    )
    for name in public_names:
        assert getattr(compatibility, name) is getattr(owner, name)
