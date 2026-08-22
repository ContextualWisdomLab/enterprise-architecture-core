"""Enterprise Architecture Core foundation validation and process surface."""

from .service import (
    BindAddress,
    HealthReport,
    ReadinessReport,
    TargetStateApprovalRequest,
    build_approval_authorization_config,
    build_health_report,
    build_readiness_report,
    build_target_state_approval_writer,
    classify_request,
    create_service_server,
    parse_target_state_approval_request,
    resolve_bind_address,
)
from .service import (
    main as serve_foundation,
)
from .validation import (
    ContractValidationError,
    RepositoryReport,
    validate_asyncapi_document,
    validate_connector_catalog,
    validate_migration_inventory,
    validate_migration_sql,
    validate_openapi_document,
    validate_openapi_runtime_surface,
    validate_repository,
)

__all__ = [
    "BindAddress",
    "ContractValidationError",
    "HealthReport",
    "ReadinessReport",
    "RepositoryReport",
    "TargetStateApprovalRequest",
    "build_approval_authorization_config",
    "build_health_report",
    "build_readiness_report",
    "build_target_state_approval_writer",
    "classify_request",
    "create_service_server",
    "parse_target_state_approval_request",
    "resolve_bind_address",
    "serve_foundation",
    "validate_asyncapi_document",
    "validate_connector_catalog",
    "validate_migration_inventory",
    "validate_migration_sql",
    "validate_openapi_document",
    "validate_openapi_runtime_surface",
    "validate_repository",
]

__version__ = "0.1.0"
