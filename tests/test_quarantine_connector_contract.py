"""Quarantine runtime Context Map boundary regressions."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from ea_core_foundation import ContractValidationError, validate_connector_catalog


_CONNECTOR_NAME = "quarantine_sandbox_runtime"
_EXPECTED_OWNER = "ContextualWisdomLab/quarantine-sandbox-runtime"
_EXPECTED_AUTHORITY_SCOPE = ["isolation_runtime", "artifact_analysis_evidence"]
_EXPECTED_CAPABILITIES = ["application_service_lease", "artifact_analysis_evidence"]
_EXPECTED_INTERACTIONS = [
    {
        "source_repository": "ContextualWisdomLab/contextual-orchestrator",
        "target_capability": "application_service_lease",
    },
    {
        "source_repository": "ContextualWisdomLab/wardnet",
        "target_capability": "artifact_analysis_evidence",
    },
]
_EXPECTED_PROJECTION_SCOPE = [
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
]
_EXPECTED_FORBIDDEN_AUTHORITATIVE_FACTS = [
    "malware_verdict",
    "artifact_risk_score",
]
_EXPECTED_PROHIBITED_INTEGRATIONS = [
    "direct_database_access",
    "source_copy",
]


def _catalog(repository_root: Path) -> dict:
    """Load the checked-in connector catalog as mutable acceptance input."""

    return json.loads(
        (repository_root / "contracts/connectors/ecosystem.json").read_text(
            encoding="utf-8"
        )
    )


def _quarantine_connector(document: dict) -> dict:
    """Return the explicit quarantine runtime boundary from a catalog document."""

    return next(
        connector
        for connector in document["connectors"]
        if connector.get("connector_name") == _CONNECTOR_NAME
    )


def test_checked_in_catalog_declares_quarantine_runtime_boundary(
    repository_root,
) -> None:
    """EA names the reusable runtime without absorbing verdict or policy authority."""

    document = _catalog(repository_root)
    names = {connector["connector_name"] for connector in document["connectors"]}
    assert _CONNECTOR_NAME in names

    connector = _quarantine_connector(document)
    assert connector["owner_repository"] == _EXPECTED_OWNER
    assert connector["authority_scope"] == _EXPECTED_AUTHORITY_SCOPE
    assert connector["deployment_boundary"] == "independent_reusable_service"
    assert connector["capabilities"] == _EXPECTED_CAPABILITIES
    assert connector["required_interactions"] == _EXPECTED_INTERACTIONS
    assert connector["architecture_projection_scope"] == _EXPECTED_PROJECTION_SCOPE
    assert (
        connector["forbidden_authoritative_facts"]
        == _EXPECTED_FORBIDDEN_AUTHORITATIVE_FACTS
    )
    assert connector["prohibited_integrations"] == _EXPECTED_PROHIBITED_INTEGRATIONS
    assert validate_connector_catalog(document) == len(document["connectors"])


def test_quarantine_connector_is_required_exactly_once(repository_root) -> None:
    """The Context Map cannot omit or duplicate its reusable isolation boundary."""

    document = _catalog(repository_root)
    connector = deepcopy(_quarantine_connector(document))
    document["connectors"] = [
        item
        for item in document["connectors"]
        if item["connector_name"] != _CONNECTOR_NAME
    ]
    with pytest.raises(
        ContractValidationError,
        match="exactly one quarantine_sandbox_runtime",
    ):
        validate_connector_catalog(document)

    document = _catalog(repository_root)
    duplicate = deepcopy(connector)
    duplicate["connector_name"] = "quarantine_sandbox_runtime_copy"
    document["connectors"].append(duplicate)
    validate_connector_catalog(document)

    duplicate["connector_name"] = _CONNECTOR_NAME
    with pytest.raises(ContractValidationError, match="duplicate connector_name"):
        validate_connector_catalog(document)


@pytest.mark.parametrize(
    ("field", "replacement", "message"),
    [
        ("owner_repository", "ContextualWisdomLab/wardnet", "owner_repository"),
        ("authority_scope", ["maliciousness_verdict"], "authority_scope"),
        ("deployment_boundary", "embedded_library", "independently deployable"),
        ("capabilities", ["artifact_analysis_evidence"], "capabilities"),
        ("required_interactions", [], "required directional interactions"),
        (
            "architecture_projection_scope",
            ["malware_verdict"],
            "architecture projection scope",
        ),
        (
            "forbidden_authoritative_facts",
            ["malware_verdict"],
            "forbidden authoritative facts",
        ),
        ("prohibited_integrations", ["direct_database_access"], "source copy"),
    ],
)
def test_quarantine_boundary_fields_fail_closed(
    repository_root,
    field,
    replacement,
    message,
) -> None:
    """Missing runtime ownership and ACL facts cannot silently pass catalog admission."""

    document = _catalog(repository_root)
    connector = _quarantine_connector(document)
    connector[field] = replacement

    with pytest.raises(ContractValidationError, match=message):
        validate_connector_catalog(document)


def test_quarantine_interactions_are_directional_and_caller_owned(
    repository_root,
) -> None:
    """Orchestrator and Wardnet call distinct runtime capabilities without ownership drift."""

    document = _catalog(repository_root)
    connector = _quarantine_connector(document)
    bad_interactions = deepcopy(connector["required_interactions"])
    bad_interactions[0]["source_repository"] = "ContextualWisdomLab/wardnet"
    connector["required_interactions"] = bad_interactions

    with pytest.raises(
        ContractValidationError,
        match="required directional interactions",
    ):
        validate_connector_catalog(document)
