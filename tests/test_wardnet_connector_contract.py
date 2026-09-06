"""Wardnet Context Map authority-boundary regressions."""

import json
from pathlib import Path

import pytest

from ea_core_foundation import ContractValidationError, validate_connector_catalog

_CONNECTOR_NAME = "wardnet_security_evidence"
_EXPECTED_OWNER = "ContextualWisdomLab/wardnet"
_EXPECTED_PROJECTION_TRUTH_STATUSES = ["observed"]
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


def _wardnet_connector(document: dict) -> dict:
    """Return the Wardnet evidence boundary from a catalog document."""

    return next(
        connector
        for connector in document["connectors"]
        if connector.get("connector_name") == _CONNECTOR_NAME
    )


def test_checked_in_wardnet_connector_keeps_verdicts_out_of_ea_authority(
    repository_root,
) -> None:
    """Admit Wardnet architecture evidence without importing verdict authority."""

    document = _catalog(repository_root)
    connector = _wardnet_connector(document)

    assert connector["owner_repository"] == _EXPECTED_OWNER
    assert connector["direction_code"] == "inbound_evidence"
    assert connector["exchange_kind"] == "context_assertion_cloudevent"
    assert connector["ea_core_owns"] is False
    assert (
        connector["projection_truth_statuses"]
        == _EXPECTED_PROJECTION_TRUTH_STATUSES
    )
    assert (
        connector["forbidden_authoritative_facts"]
        == _EXPECTED_FORBIDDEN_AUTHORITATIVE_FACTS
    )
    assert (
        connector["prohibited_integrations"]
        == _EXPECTED_PROHIBITED_INTEGRATIONS
    )
    assert validate_connector_catalog(document) == len(document["connectors"])


@pytest.mark.parametrize(
    ("field", "replacement", "message"),
    [
        (
            "owner_repository",
            "ContextualWisdomLab/enterprise-architecture-core",
            "Wardnet",
        ),
        ("direction_code", "inbound_projection", "inbound_evidence"),
        ("exchange_kind", "canonical_asset_uri", "Context Assertion"),
        ("ea_core_owns", True, "outside EA Core ownership"),
        ("projection_truth_statuses", ["authoritative"], "observed"),
        (
            "forbidden_authoritative_facts",
            ["malware_verdict"],
            "artifact risk score",
        ),
        ("prohibited_integrations", ["direct_database_access"], "source copy"),
    ],
)
def test_wardnet_authority_boundary_fails_closed(
    repository_root,
    field,
    replacement,
    message,
) -> None:
    """Reject connector drift that imports Wardnet product truth into EA."""

    document = _catalog(repository_root)
    connector = _wardnet_connector(document)
    connector[field] = replacement

    with pytest.raises(ContractValidationError, match=message):
        validate_connector_catalog(document)
