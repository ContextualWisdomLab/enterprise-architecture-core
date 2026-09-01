"""Validation for Context Fabric connector ownership and contract bindings."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from . import validation_data_management_recheck_status as base

ContractValidationError = base.ContractValidationError
RepositoryReport = base.RepositoryReport

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
_QUARANTINE_CONNECTOR_NAME = "quarantine_sandbox_runtime"
_QUARANTINE_OWNER_REPOSITORY = "ContextualWisdomLab/quarantine-sandbox-runtime"
_QUARANTINE_DIRECTION_CODE = "inbound_projection"
_QUARANTINE_EXCHANGE_KIND = "context_assertion_cloudevent"
_QUARANTINE_AUTHORITY_SCOPE = (
    "isolation_runtime",
    "artifact_analysis_evidence",
)
_QUARANTINE_CAPABILITIES = (
    "application_service_lease",
    "artifact_analysis_evidence",
)
_QUARANTINE_INTERACTIONS = (
    {
        "source_repository": "ContextualWisdomLab/contextual-orchestrator",
        "target_capability": "application_service_lease",
    },
    {
        "source_repository": "ContextualWisdomLab/wardnet",
        "target_capability": "artifact_analysis_evidence",
    },
)
_QUARANTINE_PROJECTION_SCOPE = (
    "runtime_identity",
    "backend_technology",
    "technology_provider",
    "technology_version",
    "lifecycle",
    "architecture_risk_context",
    "ownership",
    "remediation",
    "transformation",
    "attestation_provenance",
)
_QUARANTINE_FORBIDDEN_AUTHORITATIVE_FACTS = (
    "malware_verdict",
    "artifact_risk_score",
)
_QUARANTINE_PROHIBITED_INTEGRATIONS = (
    "direct_database_access",
    "source_copy",
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


def _validate_quarantine_runtime_boundary(connector: Mapping[str, Any]) -> None:
    """Keep quarantine isolation/evidence reusable without importing verdict authority."""

    if connector.get("owner_repository") != _QUARANTINE_OWNER_REPOSITORY:
        raise ContractValidationError(
            "quarantine runtime owner_repository must be "
            "ContextualWisdomLab/quarantine-sandbox-runtime"
        )
    if connector.get("direction_code") != _QUARANTINE_DIRECTION_CODE:
        raise ContractValidationError(
            "quarantine runtime direction_code must remain inbound_projection"
        )
    if connector.get("exchange_kind") != _QUARANTINE_EXCHANGE_KIND:
        raise ContractValidationError(
            "quarantine runtime exchange_kind must remain context_assertion_cloudevent"
        )
    if connector.get("ea_core_owns") is not False:
        raise ContractValidationError(
            "quarantine runtime ea_core_owns must remain false"
        )
    if connector.get("authority_scope") != list(_QUARANTINE_AUTHORITY_SCOPE):
        raise ContractValidationError(
            "quarantine runtime authority_scope must remain isolation runtime and "
            "artifact-analysis evidence"
        )
    if connector.get("deployment_boundary") != "independent_reusable_service":
        raise ContractValidationError(
            "quarantine runtime must remain independently deployable and reusable"
        )
    if connector.get("capabilities") != list(_QUARANTINE_CAPABILITIES):
        raise ContractValidationError(
            "quarantine runtime capabilities must include application-service lease "
            "and artifact-analysis evidence"
        )
    if connector.get("required_interactions") != list(_QUARANTINE_INTERACTIONS):
        raise ContractValidationError(
            "quarantine runtime must declare required directional interactions from "
            "contextual-orchestrator and Wardnet"
        )
    if connector.get("architecture_projection_scope") != list(
        _QUARANTINE_PROJECTION_SCOPE
    ):
        raise ContractValidationError(
            "quarantine runtime architecture projection scope must remain bounded to "
            "runtime/backend/lifecycle/remediation context"
        )
    if connector.get("forbidden_authoritative_facts") != list(
        _QUARANTINE_FORBIDDEN_AUTHORITATIVE_FACTS
    ):
        raise ContractValidationError(
            "quarantine runtime must declare malware verdict and artifact risk score "
            "as forbidden authoritative facts"
        )
    prohibited_integrations = connector.get("prohibited_integrations")
    if prohibited_integrations != list(_QUARANTINE_PROHIBITED_INTEGRATIONS):
        raise ContractValidationError(
            "quarantine runtime boundary must prohibit direct database access and "
            "source copy"
        )


def _require_quarantine_runtime_boundary(document: Mapping[str, Any]) -> None:
    """Require one canonical name and one canonical owner for quarantine runtime."""

    quarantine_connectors = [
        connector
        for connector in document["connectors"]
        if connector.get("connector_name") == _QUARANTINE_CONNECTOR_NAME
    ]
    if len(quarantine_connectors) != 1:
        raise ContractValidationError(
            "connector catalog must declare exactly one quarantine_sandbox_runtime"
        )
    quarantine_connector = quarantine_connectors[0]
    _validate_quarantine_runtime_boundary(quarantine_connector)

    owner_boundaries = [
        connector
        for connector in document["connectors"]
        if connector.get("owner_repository") == _QUARANTINE_OWNER_REPOSITORY
    ]
    if owner_boundaries != [quarantine_connector]:
        raise ContractValidationError(
            "connector catalog must declare exactly one quarantine runtime owner boundary"
        )


def validate_connector_catalog(document: Mapping[str, Any]) -> int:
    """Validate connector ownership plus shared Context Graph release bindings."""

    connector_count = base.validate_connector_catalog(document)
    for connector in document["connectors"]:
        _validate_context_contract_binding(connector)
    _require_quarantine_runtime_boundary(document)
    return connector_count


def validate_repository(repository_root: Path) -> RepositoryReport:
    """Validate repository artifacts plus the connector release-manifest binding."""

    report = base.validate_repository(repository_root)
    connector_path = repository_root / "contracts/connectors/ecosystem.json"
    connector_document = json.loads(connector_path.read_text(encoding="utf-8"))
    validate_connector_catalog(connector_document)
    return report
