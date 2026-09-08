"""Compatibility facade for Cross-Domain Evidence connector validation."""

from collections.abc import Mapping
from typing import Any

from .cross_domain_evidence.connector_catalog import (
    ContractValidationError,
    RepositoryReport,
    validate_connector_catalog as _validate_connector_catalog,
    validate_repository,
)


def validate_connector_catalog(document: Mapping[str, Any]) -> int:
    """Validate the catalog and fail closed on Noema ownership drift."""

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
    return connector_count


__all__ = [
    "ContractValidationError",
    "RepositoryReport",
    "validate_connector_catalog",
    "validate_repository",
]
