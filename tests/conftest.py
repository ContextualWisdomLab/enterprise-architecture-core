"""Shared foundation test fixtures."""

import json
from pathlib import Path

import pytest


@pytest.fixture
def repository_root() -> Path:
    """Return the repository root used by integration-style tests."""

    return Path(__file__).resolve().parents[1]


@pytest.fixture
def openapi_document(repository_root: Path) -> dict[str, object]:
    """Return a mutable OpenAPI fixture loaded from the repository."""

    return json.loads(
        (repository_root / "contracts/openapi.json").read_text(encoding="utf-8")
    )


@pytest.fixture
def asyncapi_document(repository_root: Path) -> dict[str, object]:
    """Return a mutable AsyncAPI fixture loaded from the repository."""

    return json.loads(
        (repository_root / "contracts/asyncapi.json").read_text(encoding="utf-8")
    )
