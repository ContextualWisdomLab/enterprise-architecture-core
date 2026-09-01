"""Validation for Context Fabric connector ownership and contract bindings."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from . import validation_data_management_recheck_status as base

ContractValidationError = base.ContractValidationError
RepositoryReport = base.RepositoryReport
validate_asyncapi_document = base.validate_asyncapi_document
validate_migration_inventory = base.validate_migration_inventory
validate_migration_sql = base.validate_migration_sql
validate_openapi_document = base.validate_openapi_document
validate_openapi_runtime_surface = base.validate_openapi_runtime_surface

_CONTEXT_CONTRACT_BOUND_DIRECTIONS = frozenset(
    {
        "shared_envelope",
        "inbound_projection",
        "inbound_evidence",
        "inbound_proposal",
        "outbound_event",
    }
)
_CONTEXT_CONTRACT_DEPENDENCY = "contracts/context-graph-dependency.json"
_OWNER_REPOSITORY_PREFIX = "ContextualWisdomLab/"
_PRESERVED_CONTEXT_SEMANTICS = (
    "canonical_reference",
    "source_reference",
    "truth_status",
    "effective_time",
    "system_time",
    "provenance",
)


def _validate_context_contract_binding(connector: Mapping[str, Any]) -> None:
    """Require architecture projections to bind one canonical owner and release."""

    owner_repository = connector.get("owner_repository")
    if not str(owner_repository).startswith(_OWNER_REPOSITORY_PREFIX):
        raise ContractValidationError(
            "connector owner_repository must name a canonical "
            "ContextualWisdomLab repository"
        )
    if connector.get("direction_code") not in _CONTEXT_CONTRACT_BOUND_DIRECTIONS:
        return
    if connector.get("context_contract_dependency") != _CONTEXT_CONTRACT_DEPENDENCY:
        raise ContractValidationError(
            "Context Fabric projection must bind context-graph-dependency.json"
        )
    preserved_semantics = connector.get("preserved_semantics")
    if preserved_semantics != list(_PRESERVED_CONTEXT_SEMANTICS):
        raise ContractValidationError(
            "Context Fabric projection must preserve exact context semantics"
        )


def validate_connector_catalog(document: Mapping[str, Any]) -> int:
    """Validate connector ownership plus shared Context Graph release bindings."""

    connector_count = base.validate_connector_catalog(document)
    for connector_value in document["connectors"]:
        connector = base.core._require_mapping(connector_value, "connector")
        _validate_context_contract_binding(connector)
    return connector_count


def validate_repository(repository_root: Path) -> RepositoryReport:
    """Validate repository artifacts plus the connector release-manifest binding."""

    report = base.validate_repository(repository_root)
    connector_path = repository_root / "contracts/connectors/ecosystem.json"
    connector_document = json.loads(connector_path.read_text(encoding="utf-8"))
    validate_connector_catalog(connector_document)
    return report
