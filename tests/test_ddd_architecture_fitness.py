"""Machine-check bounded-context ownership and known DDD debt."""

import ast
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
    """Block new catch-all directories and modules from accumulating domain behavior."""

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
    """Require external product integration through contracts and ACLs, not implementations."""

    offenders: list[str] = []
    package_root = Path("src/ea_core_foundation")
    for source_path in sorted(package_root.rglob("*.py")):
        tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
        for node in ast.walk(tree):
            imported_roots: list[str] = []
            if isinstance(node, ast.Import):
                imported_roots.extend(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_roots.append(node.module.split(".", 1)[0])
            for imported_root in imported_roots:
                if imported_root in _FOREIGN_PRODUCT_PACKAGES:
                    offenders.append(f"{source_path}:{imported_root}")
    assert offenders == []


def test_baseline_keeps_historical_package_debt_visible() -> None:
    """Do not let the foundation-era package and broad service module become invisible debt."""

    baseline = Path("docs/product-technical-gap-baseline.md").read_text(encoding="utf-8")
    assert "src/ea_core_foundation" in baseline
    assert "src/ea_core_foundation/service.py" in baseline
    assert "Open DDD debt" in baseline
    assert "Anti-Corruption Layer" in baseline
