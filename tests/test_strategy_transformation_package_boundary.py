"""Strategy & Transformation bounded-context ownership regressions."""

import ast
import importlib
from pathlib import Path


def test_transformation_completion_has_bounded_context_owner_path() -> None:
    """Keep transformation-completion behavior out of the foundation root."""

    owner_path = Path(
        "src/ea_core_foundation/strategy_transformation/complete.py"
    )
    compatibility_path = Path("src/ea_core_foundation/complete.py")
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
        and node.module == "strategy_transformation.complete"
        for node in compatibility_tree.body
    )


def test_completion_runtime_uses_the_bounded_owner_not_the_legacy_facade() -> None:
    """Keep internal completion composition on the canonical owner path."""

    runtime_path = Path("src/ea_core_foundation/completion_runtime.py")
    runtime_tree = ast.parse(
        runtime_path.read_text(encoding="utf-8"),
        filename=str(runtime_path),
    )
    imports = [
        node
        for node in runtime_tree.body
        if isinstance(node, ast.ImportFrom)
    ]
    assert any(
        node.level == 1 and node.module == "strategy_transformation.complete"
        for node in imports
    )
    assert not any(
        node.level == 1 and node.module == "complete"
        for node in imports
    )


def test_legacy_transformation_completion_is_a_compatibility_alias() -> None:
    """Preserve the completion API while moving its behavior to its owner."""

    compatibility = importlib.import_module("ea_core_foundation.complete")
    owner = importlib.import_module(
        "ea_core_foundation.strategy_transformation.complete"
    )
    public_names = (
        "TargetStateCompleteRequest",
        "build_complete_authorization_config",
        "build_target_state_complete_writer",
        "parse_target_state_complete_request",
    )
    for name in public_names:
        assert getattr(compatibility, name) is getattr(owner, name)
