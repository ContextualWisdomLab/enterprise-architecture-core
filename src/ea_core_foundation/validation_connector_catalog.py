"""Compatibility facade for Cross-Domain Evidence connector validation."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .cross_domain_evidence.connector_catalog import (
    ContractValidationError,
    RepositoryReport,
    validate_connector_catalog as _validate_connector_catalog,
    validate_repository as _validate_repository,
)
from .cross_domain_evidence.quarantine_runtime_boundary import (
    validate_quarantine_application_service_runtime_controls,
)


def validate_connector_catalog(document: Mapping[str, Any]) -> int:
    """Validate the catalog plus the explicit quarantine runtime control boundary."""

    connector_count = _validate_connector_catalog(document)
    quarantine = next(
        connector
        for connector in document["connectors"]
        if connector.get("connector_name") == "quarantine_sandbox_runtime"
    )
    validate_quarantine_application_service_runtime_controls(quarantine)
    return connector_count


def validate_repository(repository_root: Path) -> RepositoryReport:
    """Validate repository artifacts including the quarantine runtime boundary."""

    report = _validate_repository(repository_root)
    connector_path = repository_root / "contracts/connectors/ecosystem.json"
    document = json.loads(connector_path.read_text(encoding="utf-8"))
    validate_connector_catalog(document)
    return report


__all__ = [
    "ContractValidationError",
    "RepositoryReport",
    "validate_connector_catalog",
    "validate_repository",
]
