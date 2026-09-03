"""Runtime composition regressions for canonical bounded-context imports."""

import ast
from pathlib import Path

_RUNTIME_PATHS = (
    Path("src/ea_core_foundation/completion_runtime.py"),
    Path("src/ea_core_foundation/verification_runtime.py"),
    Path("src/ea_core_foundation/monitoring_runtime.py"),
    Path("src/ea_core_foundation/replan_runtime.py"),
)
_FORBIDDEN_ROOT_FACADES = {
    "authorization",
    "service",
    "start",
    "complete",
    "verify",
    "monitor",
    "replan",
    "data_management_recheck",
    "data_management_recheck_status",
    "portfolio",
}


def test_runtime_extensions_compose_canonical_bounded_context_owners() -> None:
    """Do not route internal runtime composition through historical root facades."""

    for runtime_path in _RUNTIME_PATHS:
        tree = ast.parse(
            runtime_path.read_text(encoding="utf-8"),
            filename=str(runtime_path),
        )
        imports = [
            node for node in tree.body if isinstance(node, ast.ImportFrom)
        ]
        legacy = {
            node.module
            for node in imports
            if node.level == 1 and node.module in _FORBIDDEN_ROOT_FACADES
        }
        assert legacy == set(), (
            f"{runtime_path} must compose canonical bounded-context owners; "
            f"legacy facades: {sorted(legacy)}"
        )
