"""Ecosystem connector catalog regressions."""

import json
from copy import deepcopy
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
    "github_governance",
    "bandscope_product_context",
    "orgmetra_organization_context",
    "tepp_learning_context",
    "contextual_orchestrator_proposal",
    "wardnet_security_evidence",
    "appguardrail_security_evidence",
    "governance_risk_control_evidence",
}


def test_checked_in_connector_catalog_covers_context_fabric_projection_neighbors(
    repository_root,
) -> None:
    """The catalog names every accepted Context Fabric projection owner explicitly."""

    document = json.loads(
        (repository_root / "contracts/connectors/ecosystem.json").read_text(
            encoding="utf-8"
        )
    )
    assert validate_connector_catalog(document) == len(_REQUIRED_CONTEXT_FABRIC_CONNECTORS)
    names = {connector["connector_name"] for connector in document["connectors"]}
    assert names == _REQUIRED_CONTEXT_FABRIC_CONNECTORS


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
    """Connector identities follow the same two-word naming rule as database objects."""

    document = _valid_catalog(repository_root)
    document["connectors"][0] = []
    with pytest.raises(ContractValidationError, match="connector must be an object"):
        validate_connector_catalog(document)

    document = _valid_catalog(repository_root)
    document["connectors"][0]["connector_name"] = 1
    with pytest.raises(
        ContractValidationError, match="connector_name must be a string"
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
