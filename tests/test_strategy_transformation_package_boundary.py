"""Strategy & Transformation bounded-context ownership regressions."""

import ast
import importlib
from pathlib import Path

_BEHAVIOR_NODES = (
    ast.ClassDef,
    ast.FunctionDef,
    ast.AsyncFunctionDef,
    ast.If,
    ast.For,
    ast.While,
    ast.Try,
    ast.With,
)


def _assert_behavior_free_facade(
    compatibility_path: Path,
    owner_module: str,
) -> None:
    """Require a legacy root path to remain an import-only compatibility facade."""

    compatibility_tree = ast.parse(
        compatibility_path.read_text(encoding="utf-8"),
        filename=str(compatibility_path),
    )
    assert not any(
        isinstance(node, _BEHAVIOR_NODES) for node in ast.walk(compatibility_tree)
    )
    assert any(
        isinstance(node, ast.ImportFrom)
        and node.level == 1
        and node.module == owner_module
        for node in compatibility_tree.body
    )


def test_transformation_completion_has_bounded_context_owner_path() -> None:
    """Keep transformation-completion behavior out of the foundation root."""

    owner_path = Path("src/ea_core_foundation/strategy_transformation/complete.py")
    assert owner_path.is_file()
    _assert_behavior_free_facade(
        Path("src/ea_core_foundation/complete.py"),
        "strategy_transformation.complete",
    )


def test_transformation_start_has_bounded_context_owner_path() -> None:
    """Keep transformation-start behavior out of the foundation root."""

    owner_path = Path("src/ea_core_foundation/strategy_transformation/start.py")
    assert owner_path.is_file()
    _assert_behavior_free_facade(
        Path("src/ea_core_foundation/start.py"),
        "strategy_transformation.start",
    )


def test_target_state_verification_has_bounded_context_owner_path() -> None:
    """Keep target-state verification behavior out of the foundation root."""

    owner_path = Path("src/ea_core_foundation/strategy_transformation/verify.py")
    assert owner_path.is_file()
    _assert_behavior_free_facade(
        Path("src/ea_core_foundation/verify.py"),
        "strategy_transformation.verify",
    )


def test_completion_runtime_uses_bounded_transformation_command_owners() -> None:
    """Keep completion composition on canonical transformation command ports."""

    runtime_path = Path("src/ea_core_foundation/completion_runtime.py")
    runtime_tree = ast.parse(
        runtime_path.read_text(encoding="utf-8"),
        filename=str(runtime_path),
    )
    imports = [
        node for node in runtime_tree.body if isinstance(node, ast.ImportFrom)
    ]
    for owner_module in (
        "strategy_transformation.complete",
        "strategy_transformation.start",
    ):
        assert any(
            node.level == 1 and node.module == owner_module for node in imports
        )
    assert not any(
        node.level == 1 and node.module in {"complete", "start"}
        for node in imports
    )


def test_verification_runtime_uses_bounded_transformation_command_owner() -> None:
    """Keep verification composition on the canonical transformation command port."""

    runtime_path = Path("src/ea_core_foundation/verification_runtime.py")
    runtime_tree = ast.parse(
        runtime_path.read_text(encoding="utf-8"),
        filename=str(runtime_path),
    )
    imports = [
        node for node in runtime_tree.body if isinstance(node, ast.ImportFrom)
    ]
    assert any(
        node.level == 1 and node.module == "strategy_transformation.verify"
        for node in imports
    )
    assert not any(
        node.level == 1 and node.module == "verify" for node in imports
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


def test_legacy_transformation_start_is_a_compatibility_alias() -> None:
    """Preserve the start API while moving its behavior to its owner."""

    compatibility = importlib.import_module("ea_core_foundation.start")
    owner = importlib.import_module("ea_core_foundation.strategy_transformation.start")
    public_names = (
        "TargetStateStartRequest",
        "build_start_authorization_config",
        "build_target_state_start_writer",
        "parse_target_state_start_request",
    )
    for name in public_names:
        assert getattr(compatibility, name) is getattr(owner, name)


def test_legacy_target_state_verification_is_a_compatibility_alias() -> None:
    """Preserve verification API identity while moving behavior to its owner."""

    compatibility = importlib.import_module("ea_core_foundation.verify")
    owner = importlib.import_module("ea_core_foundation.strategy_transformation.verify")
    public_names = (
        "TargetStateVerificationRequest",
        "build_target_state_verification_writer",
        "build_verification_authorization_config",
        "parse_target_state_verification_request",
    )
    for name in public_names:
        assert getattr(compatibility, name) is getattr(owner, name)


def test_target_state_monitoring_has_bounded_context_owner_path() -> None:
    """Keep target-state monitoring behavior out of the foundation root."""

    owner_path = Path("src/ea_core_foundation/strategy_transformation/monitor.py")
    assert owner_path.is_file()
    _assert_behavior_free_facade(
        Path("src/ea_core_foundation/monitor.py"),
        "strategy_transformation.monitor",
    )


def test_monitoring_runtime_uses_canonical_strategy_transformation_ports() -> None:
    """Keep monitoring composition on canonical Strategy & Transformation ports."""

    runtime_path = Path("src/ea_core_foundation/monitoring_runtime.py")
    runtime_tree = ast.parse(
        runtime_path.read_text(encoding="utf-8"),
        filename=str(runtime_path),
    )
    imports = [
        node for node in runtime_tree.body if isinstance(node, ast.ImportFrom)
    ]
    for owner_module in (
        "strategy_transformation.complete",
        "strategy_transformation.monitor",
        "strategy_transformation.start",
    ):
        assert any(
            node.level == 1 and node.module == owner_module for node in imports
        )
    assert not any(
        node.level == 1 and node.module in {"complete", "monitor", "start"}
        for node in imports
    )


def test_strategy_owner_modules_use_canonical_shared_adapters() -> None:
    """Keep bounded strategy behavior off historical root shared-adapter facades."""

    for owner_path in (
        Path("src/ea_core_foundation/strategy_transformation/complete.py"),
        Path("src/ea_core_foundation/strategy_transformation/monitor.py"),
        Path("src/ea_core_foundation/strategy_transformation/start.py"),
        Path("src/ea_core_foundation/strategy_transformation/verify.py"),
    ):
        owner_tree = ast.parse(
            owner_path.read_text(encoding="utf-8"),
            filename=str(owner_path),
        )
        imports = [
            node for node in owner_tree.body if isinstance(node, ast.ImportFrom)
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
