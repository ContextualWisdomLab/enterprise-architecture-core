"""Regressions that keep operator-facing configuration aligned with public contracts."""

from pathlib import Path


def _example_environment_keys(repository_root: Path) -> set[str]:
    """Return configuration keys documented by the deployable environment example."""

    return {
        line.split("=", 1)[0]
        for line in (repository_root / ".env.example")
        .read_text(encoding="utf-8")
        .splitlines()
        if line and not line.startswith("#") and "=" in line
    }


def test_environment_example_covers_declared_keyverse_configuration(
    repository_root: Path,
    openapi_document,
) -> None:
    """Every fail-closed Keyverse setting in OpenAPI is deployable from the example."""

    required = set(openapi_document["x-keyverse-contract"]["requiredConfiguration"])
    assert required <= _example_environment_keys(repository_root)


def test_readme_names_every_buyer_facing_v1_operation(
    repository_root: Path,
    openapi_document,
) -> None:
    """Operators can discover every implemented buyer-facing v1 route without source."""

    readme = (repository_root / "README.md").read_text(encoding="utf-8")
    public_paths = {
        path for path in openapi_document["paths"] if path.startswith("/v1/")
    }
    assert public_paths
    assert all(path in readme for path in public_paths)
