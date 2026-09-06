"""Contextual Orchestrator proposal-boundary regressions."""

import json
from pathlib import Path

import pytest

from ea_core_foundation import ContractValidationError, validate_connector_catalog

_CONNECTOR_NAME = "contextual_orchestrator_proposal"
_EXPECTED_TRUTH_STATUSES = ["proposed", "inferred"]


def _catalog(repository_root: Path) -> dict:
    """Load the checked-in connector catalog as mutable contract input."""

    return json.loads(
        (repository_root / "contracts/connectors/ecosystem.json").read_text(
            encoding="utf-8"
        )
    )


def _connector(document: dict) -> dict:
    """Return the Contextual Orchestrator proposal boundary."""

    return next(
        connector
        for connector in document["connectors"]
        if connector.get("connector_name") == _CONNECTOR_NAME
    )


def test_checked_in_orchestrator_proposal_restricts_truth_dispositions(
    repository_root,
) -> None:
    """Architecture suggestions remain proposed/inferred until an EA command decides."""

    document = _catalog(repository_root)
    connector = _connector(document)

    assert connector["projection_truth_statuses"] == _EXPECTED_TRUTH_STATUSES
    assert validate_connector_catalog(document) == len(document["connectors"])


@pytest.mark.parametrize(
    "replacement",
    [
        ["authoritative"],
        ["observed"],
        ["proposed", "inferred", "authoritative"],
        ["inferred", "proposed"],
        [],
        None,
    ],
)
def test_orchestrator_proposal_rejects_noncanonical_truth_dispositions(
    repository_root,
    replacement,
) -> None:
    """Prose alone must not permit producer suggestions to become EA authority."""

    document = _catalog(repository_root)
    connector = _connector(document)
    connector["projection_truth_statuses"] = replacement

    with pytest.raises(
        ContractValidationError,
        match="Contextual Orchestrator proposal.*proposed.*inferred",
    ):
        validate_connector_catalog(document)
