"""Validation utilities for the Enterprise Architecture Core foundation."""

from .validation import (
    ContractValidationError,
    RepositoryReport,
    validate_asyncapi_document,
    validate_migration_inventory,
    validate_migration_sql,
    validate_openapi_document,
    validate_repository,
)

__all__ = [
    "ContractValidationError",
    "RepositoryReport",
    "validate_asyncapi_document",
    "validate_migration_inventory",
    "validate_migration_sql",
    "validate_openapi_document",
    "validate_repository",
]

__version__ = "0.1.0"
