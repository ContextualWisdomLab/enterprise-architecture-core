"""Machine-check bounded-context ownership and known DDD debt."""

import ast
import importlib
from pathlib import Path

_REQUIRED_DDD_DOCUMENTS = (
    "docs/CONTEXT_MAP.md",
    "docs/UBIQUITOUS_LANGUAGE.md",
    "docs/product-technical-gap-baseline.md",
)
_FORBIDDEN_GENERIC_DIRECTORIES = {
    "common",
    "core",
    "helpers",
    "legacy",
    "lib",
    "misc",
    "models",
    "services",
    "shared",
    "utils",
}
_FORBIDDEN_NEW_GENERIC_MODULES = {
    "common.py",
    "core.py",
    "helpers.py",
    "legacy.py",
    "misc.py",
    "models.py",
    "services.py",
    "shared.py",
    "utils.py",
}
_FOREIGN_PRODUCT_PACKAGES = {
    "contextual_orchestrator",
    "lineageweave",
    "naruon",
    "pg_erd_cloud",
    "semantic_data_portal",
}


def test_canonical_ddd_documents_exist() -> None:
    """Keep the Context Map, language and correction ledger executable."""

    for relative_path in _REQUIRED_DDD_DOCUMENTS:
        path = Path(relative_path)
        assert path.is_file(), relative_path
        assert len(path.read_text(encoding="utf-8").strip()) >= 200, relative_path


def test_production_package_does_not_grow_generic_buckets() -> None:
    """Block new catch-all directories and modules from accumulating behavior."""

    package_root = Path("src/ea_core_foundation")
    directory_offenders = sorted(
        str(path.relative_to(package_root))
        for path in package_root.rglob("*")
        if path.is_dir() and path.name in _FORBIDDEN_GENERIC_DIRECTORIES
    )
    module_offenders = sorted(
        str(path.relative_to(package_root))
        for path in package_root.rglob("*.py")
        if path.name in _FORBIDDEN_NEW_GENERIC_MODULES
    )
    assert directory_offenders == []
    assert module_offenders == []


def test_domain_code_does_not_import_foreign_product_implementations() -> None:
    """Require foreign integration through contracts and ACLs, not implementations."""

    offenders: list[str] = []
    package_root = Path("src/ea_core_foundation")
    for source_path in sorted(package_root.rglob("*.py")):
        tree = ast.parse(
            source_path.read_text(encoding="utf-8"),
            filename=str(source_path),
        )
        for node in ast.walk(tree):
            imported_roots: list[str] = []
            if isinstance(node, ast.Import):
                imported_roots.extend(
                    alias.name.split(".", 1)[0] for alias in node.names
                )
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_roots.append(node.module.split(".", 1)[0])
            for imported_root in imported_roots:
                if imported_root in _FOREIGN_PRODUCT_PACKAGES:
                    offenders.append(f"{source_path}:{imported_root}")
    assert offenders == []


def test_legacy_service_path_is_only_a_compatibility_adapter() -> None:
    """Keep new decision-plane behavior out of the historical generic service path."""

    legacy_path = Path("src/ea_core_foundation/service.py")
    owner_path = Path("src/ea_core_foundation/decision_plane_http.py")
    assert owner_path.is_file()

    legacy_tree = ast.parse(
        legacy_path.read_text(encoding="utf-8"),
        filename=str(legacy_path),
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
    assert not any(isinstance(node, behavior_nodes) for node in ast.walk(legacy_tree))
    assert any(
        isinstance(node, ast.ImportFrom)
        and node.level == 1
        and node.module == "decision_plane_http"
        for node in legacy_tree.body
    )


def test_legacy_service_import_delegates_to_the_same_module_object() -> None:
    """Preserve module identity through the compatibility window."""

    legacy_module = importlib.import_module("ea_core_foundation.service")
    owner_module = importlib.import_module("ea_core_foundation.decision_plane_http")
    assert legacy_module is owner_module


def test_baseline_keeps_historical_package_debt_visible() -> None:
    """Keep the foundation-era package and remaining path debt visible."""

    baseline = Path("docs/product-technical-gap-baseline.md").read_text(
        encoding="utf-8"
    )
    assert "src/ea_core_foundation" in baseline
    assert "src/ea_core_foundation/service.py" in baseline
    assert "Open DDD debt" in baseline
    assert "Anti-Corruption Layer" in baseline


def test_baseline_tracks_the_current_protected_main_transition() -> None:
    """Keep governance prose aligned with protected main before default migration."""

    baseline = Path("docs/product-technical-gap-baseline.md").read_text(
        encoding="utf-8"
    )
    assert "default_branch=develop" in baseline
    assert "both `develop` and `main` are protected" in baseline
    assert "Change repository default to the already-protected `main`" in baseline


def test_transformation_http_adapter_has_a_bounded_owner() -> None:
    """Keep Strategy & Transformation command HTTP behavior out of root runtime.py."""

    owner_path = Path("src/ea_core_foundation/strategy_transformation/http.py")
    runtime_path = Path("src/ea_core_foundation/runtime.py")
    assert owner_path.is_file()

    owner_tree = ast.parse(
        owner_path.read_text(encoding="utf-8"),
        filename=str(owner_path),
    )
    assert any(
        isinstance(node, ast.ClassDef) and node.name == "SchedulingServiceHandler"
        for node in owner_tree.body
    )

    runtime_tree = ast.parse(
        runtime_path.read_text(encoding="utf-8"),
        filename=str(runtime_path),
    )
    assert not any(
        isinstance(node, ast.ClassDef) and node.name == "SchedulingServiceHandler"
        for node in runtime_tree.body
    )


def test_runtime_composes_the_bounded_transformation_http_adapter() -> None:
    """Require the deployable root to import the bounded HTTP adapter explicitly."""

    runtime_path = Path("src/ea_core_foundation/runtime.py")
    runtime_tree = ast.parse(
        runtime_path.read_text(encoding="utf-8"),
        filename=str(runtime_path),
    )
    assert any(
        isinstance(node, ast.ImportFrom)
        and node.level == 1
        and node.module == "strategy_transformation.http"
        and any(alias.name == "SchedulingServiceHandler" for alias in node.names)
        for node in runtime_tree.body
    )
