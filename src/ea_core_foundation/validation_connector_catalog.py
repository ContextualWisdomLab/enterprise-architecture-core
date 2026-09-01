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
_PRESERVED_CONTEXT_SEMANTICS = (
    "canonical_reference",
    "source_reference",
    "truth_status",
    "effective_time",
    "system_time",
    "provenance",
)


def _validate_context_contract_binding(connector: Mapping[str, Any]) -> None:
    """Require architecture projections to bind the one shared release manifest."""

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
    connectors = document["connectors"]
    for connector_value in connectors:
        connector = base.core._require_mapping(connector_value, "connector")
        _validate_context_contract_binding(connector)
    return connector_count


def validate_repository(repository_root: Path) -> RepositoryReport:
    """Validate repository artifacts and the connector-to-release manifest boundary."""

    report = base.validate_repository(repository_root)
    dependency_path = repository_root / _CONTEXT_CONTRACT_DEPENDENCY
    if not dependency_path.is_file():
        raise ContractValidationError(
            "missing Context Graph dependency manifest: "
            f"{_CONTEXT_CONTRACT_DEPENDENCY}"
        )
    dependency_document = json.loads(dependency_path.read_text(encoding="utf-8"))
    if dependency_document.get("contract_repository") != (
        "ContextualWisdomLab/context-graph-contracts"
    ):
        raise ContractValidationError(
            "Context Graph dependency manifest must name the canonical contract repository"
        )
    connector_path = repository_root / "contracts/connectors/ecosystem.json"
    validate_connector_catalog(json.loads(connector_path.read_text(encoding="utf-8")))
    return report
