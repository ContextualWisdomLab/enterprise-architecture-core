"""Keep the generic identity/authorization adapter on its bounded owner path."""

import ast
import importlib
from pathlib import Path

_OWNER_PATH = Path(
    "src/ea_core_foundation/identity_authorization/authorization.py"
)
_LEGACY_PATH = Path("src/ea_core_foundation/authorization.py")
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


def test_identity_authorization_has_a_bounded_generic_owner_path() -> None:
    """Keep Keyverse/OIDC runtime access behavior out of the package root."""

    assert _OWNER_PATH.is_file()
    assert _OWNER_PATH.stat().st_size > 10_000


def test_legacy_authorization_path_is_a_behavior_free_facade() -> None:
    """Preserve old imports without retaining a second authorization owner."""

    tree = ast.parse(
        _LEGACY_PATH.read_text(encoding="utf-8"),
        filename=str(_LEGACY_PATH),
    )
    assert not any(isinstance(node, _BEHAVIOR_NODES) for node in ast.walk(tree))
    assert any(
        isinstance(node, ast.ImportFrom)
        and node.level == 1
        and node.module == "identity_authorization"
        for node in tree.body
    )


def test_legacy_authorization_import_resolves_to_the_owner_module() -> None:
    """Keep monkeypatch and private compatibility behavior on one module object."""

    legacy_module = importlib.import_module("ea_core_foundation.authorization")
    owner_module = importlib.import_module(
        "ea_core_foundation.identity_authorization.authorization"
    )
    assert legacy_module is owner_module


def test_context_map_names_the_identity_authorization_owner_path() -> None:
    """Keep the Generic subdomain path visible in the executable Context Map."""

    context_map = Path("docs/CONTEXT_MAP.md").read_text(encoding="utf-8")
    assert "src/ea_core_foundation/identity_authorization/" in context_map
    assert "Identity / authorization adapter" in context_map
