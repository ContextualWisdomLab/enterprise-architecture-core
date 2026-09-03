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


def test_target_state_monitoring_has_bounded_context_owner_path() -> None:
    """Keep target-state monitoring behavior out of the foundation root."""

    owner_path = Path(
        "src/ea_core_foundation/strategy_transformation/monitor.py"
    )
    compatibility_path = Path("src/ea_core_foundation/monitor.py")
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
        and node.module == "strategy_transformation.monitor"
        for node in compatibility_tree.body
    )


def test_monitoring_runtime_uses_canonical_strategy_transformation_ports() -> None:
    """Keep monitoring composition on canonical Strategy & Transformation ports."""

    runtime_path = Path("src/ea_core_foundation/monitoring_runtime.py")
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
    assert any(
        node.level == 1 and node.module == "strategy_transformation.monitor"
        for node in imports
    )
    assert not any(
        node.level == 1 and node.module in {"complete", "monitor"}
        for node in imports
    )


def test_strategy_owner_modules_use_canonical_shared_adapters() -> None:
    """Keep bounded strategy behavior off historical root shared-adapter facades."""

    for owner_path in (
        Path("src/ea_core_foundation/strategy_transformation/complete.py"),
        Path("src/ea_core_foundation/strategy_transformation/monitor.py"),
    ):
        owner_tree = ast.parse(
            owner_path.read_text(encoding="utf-8"),
            filename=str(owner_path),
        )
        imports = [
            node
            for node in owner_tree.body
            if isinstance(node, ast.ImportFrom)
        ]
        assert not any(
            node.level == 2 and node.module in {"authorization", "service"}
            for node in imports
        )
        assert any(
            node.level == 2
            and node.module == "identity_authorization.authorization"
            for node in imports
        )
        assert any(
            node.level == 2 and node.module == "decision_plane_http"
            for node in imports
        )


def test_legacy_target_state_monitoring_is_a_compatibility_alias() -> None:
    """Preserve monitoring API identity while moving behavior to its owner."""

    compatibility = importlib.import_module("ea_core_foundation.monitor")
    owner = importlib.import_module(
        "ea_core_foundation.strategy_transformation.monitor"
    )
    public_names = (
        "TargetStateMonitoringRequest",
        "TargetStateMonitoringReader",
        "build_monitoring_authorization_config",
        "build_target_state_monitoring_reader",
        "parse_target_state_monitoring_request",
    )
    for name in public_names:
        assert getattr(compatibility, name) is getattr(owner, name)
