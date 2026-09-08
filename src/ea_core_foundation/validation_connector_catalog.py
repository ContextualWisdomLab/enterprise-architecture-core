"""Compatibility facade for Cross-Domain Evidence connector validation."""

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .cross_domain_evidence.appguardrail_security_evidence import (
    validate_appguardrail_security_evidence,
)
from .cross_domain_evidence.connector_catalog import (
    ContractValidationError,
    RepositoryReport,
    validate_connector_catalog as _validate_connector_catalog,
    validate_repository as _validate_repository,
)


def validate_connector_catalog(document: Mapping[str, Any]) -> int:
    """Validate the catalog and fail closed on foreign-authority drift."""

    connector_count = _validate_connector_catalog(document)
    noema_connectors = [
        connector
        for connector in document["connectors"]
        if connector.get("connector_name") == "noema_projection"
    ]
    if noema_connectors and noema_connectors[0].get("ea_core_owns") is not False:
        raise ContractValidationError(
            "Noema projection must remain outside EA Core ownership"
        )
    validate_appguardrail_security_evidence(document)
    return connector_count


def validate_repository(repository_root: Path) -> RepositoryReport:
    """Apply connector ownership guards to full repository validation."""

    report = _validate_repository(repository_root)
    connector_path = repository_root / "contracts/connectors/ecosystem.json"
    connector_document = json.loads(connector_path.read_text(encoding="utf-8"))
    validate_connector_catalog(connector_document)
    return report


__all__ = [
    "ContractValidationError",
    "RepositoryReport",
    "validate_connector_catalog",
    "validate_repository",
]
