"""Ecosystem connector catalog regressions."""

from copy import deepcopy
import json
from pathlib import Path

import pytest

from ea_core_foundation import ContractValidationError, validate_connector_catalog

_REQUIRED_CONTEXT_FABRIC_CONNECTORS = {
    "keyverse_oidc",
    "context_graph_contracts",
    "semantic_data_portal",
    "pg_erd_cloud",
    "lineage_weave",
    "naruon_workspace",
    "naruon_product_context",
    "github_governance",
    "bandscope_product_context",
    "orgmetra_organization_context",
    "tepp_learning_context",
    "contextual_orchestrator_proposal",
    "quarantine_sandbox_runtime",
    "wardnet_security_evidence",
    "appguardrail_security_evidence",
    "governance_risk_control_evidence",
}
_EXPECTED_OWNER_REPOSITORIES = {
    "keyverse_oidc": "ContextualWisdomLab/keyverse",
    "context_graph_contracts": "ContextualWisdomLab/context-graph-contracts",
    "semantic_data_portal": "ContextualWisdomLab/semantic-data-portal",
    "pg_erd_cloud": "ContextualWisdomLab/pg-erd-cloud",
    "lineage_weave": "ContextualWisdomLab/LineageWeave",
    "naruon_workspace": "ContextualWisdomLab/naruon",
    "naruon_product_context": "ContextualWisdomLab/naruon",
    "github_governance": "ContextualWisdomLab/.github",
    "bandscope_product_context": "ContextualWisdomLab/bandscope",
    "orgmetra_organization_context": "ContextualWisdomLab/Orgmetra",
    "tepp_learning_context": "ContextualWisdomLab/TEPP",
    "contextual_orchestrator_proposal": (
        "ContextualWisdomLab/contextual-orchestrator"
    ),
    "quarantine_sandbox_runtime": (
        "ContextualWisdomLab/quarantine-sandbox-runtime"
    ),
    "wardnet_security_evidence": "ContextualWisdomLab/wardnet",
    "appguardrail_security_evidence": "ContextualWisdomLab/appguardrail",
    "governance_risk_control_evidence": (
        "ContextualWisdomLab/governance-risk-compliance"
    ),
}
_CONTEXT_CONTRACT_BOUND_DIRECTIONS = {
    "shared_envelope",
    "inbound_projection",
    "inbound_evidence",
    "inbound_proposal",
    "outbound_event",
}
_CONTEXT_CONTRACT_DEPENDENCY = "contracts/context-graph-dependency.json"
_PRESERVED_CONTEXT_SEMANTICS = [
    "canonical_reference",
    "source_reference",
    "truth_status",
    "effective_time",
    "system_time",
    "provenance",
]


def test_checked_in_connector_catalog_covers_context_fabric_projection_neighbors(
    repository_root,
) -> None:
    """The catalog names every accepted Context Fabric projection owner explicitly."""

    document = json.loads(
        (repository_root / "contracts/connectors/ecosystem.json").read_text(
            encoding="utf-8"
        )
    )
    assert validate_connector_catalog(document) == len(
        _REQUIRED_CONTEXT_FABRIC_CONNECTORS
    )
    names = {connector["connector_name"] for connector in document["connectors"]}
    assert names == _REQUIRED_CONTEXT_FABRIC_CONNECTORS


def test_connector_catalog_uses_canonical_repository_owners(repository_root) -> None:
    """Every connector uses one fully qualified repository identity for drill-down."""

    document = _valid_catalog(repository_root)
    actual_owners = {
        connector["connector_name"]: connector["owner_repository"]
        for connector in document["connectors"]
    }
    assert actual_owners == _EXPECTED_OWNER_REPOSITORIES


def test_projection_directions_preserve_foreign_product_authority(
    repository_root,
) -> None:
    """Keep foreign facts behind explicit evidence, proposal, or projection."""

    document = _valid_catalog(repository_root)
    by_name = {
        connector["connector_name"]: connector for connector in document["connectors"]
    }
    assert by_name["semantic_data_portal"]["direction_code"] == "inbound_projection"
    assert by_name["naruon_product_context"]["direction_code"] == "inbound_projection"
    assert (
        by_name["quarantine_sandbox_runtime"]["direction_code"]
        == "inbound_projection"
    )
    assert (
        by_name["contextual_orchestrator_proposal"]["direction_code"]
        == "inbound_proposal"
    )
    for connector_name in (
        "pg_erd_cloud",
        "wardnet_security_evidence",
        "appguardrail_security_evidence",
        "governance_risk_control_evidence",
    ):
        assert by_name[connector_name]["direction_code"] == "inbound_evidence"


def test_context_projection_connectors_bind_shared_release_contract(
    repository_root,
) -> None:
    """Architecture projections bind one release manifest and preserve semantics."""

    document = _valid_catalog(repository_root)
    bound_connectors = [
        connector
        for connector in document["connectors"]
        if connector["direction_code"] in _CONTEXT_CONTRACT_BOUND_DIRECTIONS
    ]
    assert bound_connectors
    for connector in bound_connectors:
        assert (
            connector["context_contract_dependency"]
            == _CONTEXT_CONTRACT_DEPENDENCY
        )
        assert connector["preserved_semantics"] == _PRESERVED_CONTEXT_SEMANTICS


def test_connector_catalog_rejects_unbound_context_projection(repository_root) -> None:
    """A product projection cannot bypass the released dependency manifest."""

    document = _valid_catalog(repository_root)
    connector = next(
        connector
        for connector in document["connectors"]
        if connector["connector_name"] == "semantic_data_portal"
    )
    connector.pop("context_contract_dependency", None)
    with pytest.raises(
        ContractValidationError,
        match="must bind context-graph-dependency",
    ):
        validate_connector_catalog(document)


def test_connector_catalog_rejects_context_semantic_loss(repository_root) -> None:
    """Projection metadata cannot omit source, truth, time, or provenance identity."""

    document = _valid_catalog(repository_root)
    connector = next(
        connector
        for connector in document["connectors"]
        if connector["connector_name"] == "wardnet_security_evidence"
    )
    connector["preserved_semantics"] = [
        semantic
        for semantic in connector.get("preserved_semantics", [])
        if semantic != "provenance"
    ]
    with pytest.raises(
        ContractValidationError,
        match="preserve exact context semantics",
    ):
        validate_connector_catalog(document)


def test_connector_catalog_rejects_wrong_version() -> None:
    """Catalog revisions are explicit so consumers do not guess compatibility."""

    document = {"catalog_version": "2", "exchange_rule": "x", "connectors": []}
    with pytest.raises(ContractValidationError, match="catalog_version must be 1"):
        validate_connector_catalog(document)


def test_connector_catalog_requires_sql_prohibition() -> None:
    """Cross-service SQL would collapse the MSA ownership boundary."""

    document = {"catalog_version": "1", "exchange_rule": "use SQL", "connectors": []}
    with pytest.raises(ContractValidationError, match="prohibit cross-service SQL"):
        validate_connector_catalog(document)


def test_connector_catalog_requires_array() -> None:
    """Connectors are a list of independently reviewable exchange contracts."""

    document = {
        "catalog_version": "1",
        "exchange_rule": "cross-service SQL is prohibited",
        "connectors": {},
    }
    with pytest.raises(ContractValidationError, match="connectors must be an array"):
        validate_connector_catalog(document)


def test_connector_catalog_rejects_string_connector_list() -> None:
    """A string is not an array of connector objects."""

    document = {
        "catalog_version": "1",
        "exchange_rule": "cross-service SQL is prohibited",
        "connectors": "keyverse_oidc",
    }
    with pytest.raises(ContractValidationError, match="connectors must be an array"):
        validate_connector_catalog(document)


def _valid_catalog(repository_root: Path) -> dict:
    """Load the checked-in catalog as a mutable fixture."""

    return json.loads(
        (repository_root / "contracts/connectors/ecosystem.json").read_text(
            encoding="utf-8"
        )
    )


def test_connector_requires_mapping_and_two_word_name(repository_root) -> None:
    """Connector identities follow the two-word naming rule used for DB objects."""

    document = _valid_catalog(repository_root)
    document["connectors"][0] = []
    with pytest.raises(ContractValidationError, match="connector must be an object"):
        validate_connector_catalog(document)

    document = _valid_catalog(repository_root)
    document["connectors"][0]["connector_name"] = 1
    with pytest.raises(
        ContractValidationError,
        match="connector_name must be a string",
    ):
        validate_connector_catalog(document)

    document = _valid_catalog(repository_root)
    document["connectors"][0]["connector_name"] = "keyverse"
    with pytest.raises(ContractValidationError, match="two lower-snake words"):
        validate_connector_catalog(document)


def test_connector_rejects_duplicates_and_missing_owner(repository_root) -> None:
    """Each exchange has one owner repository and a unique connector name."""

    document = _valid_catalog(repository_root)
    document["connectors"].append(deepcopy(document["connectors"][0]))
    with pytest.raises(ContractValidationError, match="duplicate connector_name"):
        validate_connector_catalog(document)

    document = _valid_catalog(repository_root)
    document["connectors"][0]["owner_repository"] = ""
    with pytest.raises(ContractValidationError, match="owner_repository is required"):
        validate_connector_catalog(document)


def test_connector_rejects_local_ownership_and_empty_next_action(
    repository_root,
) -> None:
    """EA Core must not absorb neighbor systems or omit the buyer's next action."""

    document = _valid_catalog(repository_root)
    document["connectors"][0]["ea_core_owns"] = True
    with pytest.raises(ContractValidationError, match="outside EA Core ownership"):
        validate_connector_catalog(document)

    document = _valid_catalog(repository_root)
    document["connectors"][0]["next_action"] = "later"
    with pytest.raises(ContractValidationError, match="requires a next_action"):
        validate_connector_catalog(document)

    document = _valid_catalog(repository_root)
    document["connectors"][0]["next_action"] = None
    with pytest.raises(ContractValidationError, match="requires a next_action"):
        validate_connector_catalog(document)

    document = _valid_catalog(repository_root)
    document["connectors"][0]["owner_repository"] = None
    with pytest.raises(ContractValidationError, match="owner_repository is required"):
        validate_connector_catalog(document)


def test_connector_catalog_requires_the_foundation_neighbors(repository_root) -> None:
    """Removing a required neighbor silently shrinks the ecosystem contract."""

    document = _valid_catalog(repository_root)
    document["connectors"] = [
        connector
        for connector in document["connectors"]
        if connector["connector_name"] != "naruon_workspace"
    ]
    with pytest.raises(ContractValidationError, match="missing required connectors"):
        validate_connector_catalog(document)
