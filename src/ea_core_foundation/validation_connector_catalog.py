"""Compatibility facade for Cross-Domain Evidence connector validation."""

from .cross_domain_evidence.connector_catalog import (
    ContractValidationError,
    RepositoryReport,
    validate_connector_catalog,
    validate_repository,
)

__all__ = [
    "ContractValidationError",
    "RepositoryReport",
    "validate_connector_catalog",
    "validate_repository",
]
