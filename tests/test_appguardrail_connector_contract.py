"""AppGuardrail evidence-boundary regressions."""

import json
from pathlib import Path

import pytest

from ea_core_foundation import ContractValidationError, validate_connector_catalog

_CONNECTOR_NAME = "appguardrail_security_evidence"


def _catalog(repository_root: Path) -> dict:
    """Load the checked-in connector catalog as mutable acceptance input."""

    return json.loads(
        (repository_root / "contracts/connectors/ecosystem.json").read_text(
            encoding="utf-8"
        )
    )


def _connector(document: dict) -> dict:
    """Return the AppGuardrail evidence boundary."""

    return next(
        connector
        for connector in document["connectors"]
        if connector.get("connector_name") == _CONNECTOR_NAME
    )


def test_appguardrail_security_evidence_requires_explicit_truth_statuses(
    repository_root,
) -> None:
    """Evidence projections must explicitly publish their admissible truth set."""

    document = _catalog(repository_root)
    connector = _connector(document)
    connector.pop("projection_truth_statuses", None)

    with pytest.raises(
        ContractValidationError,
        match="AppGuardrail security evidence.*observed and inferred",
    ):
        validate_connector_catalog(document)


def test_appguardrail_security_evidence_cannot_become_authoritative(
    repository_root,
) -> None:
    """Scanner findings and risk analysis must remain evidence, not EA truth."""

    document = _catalog(repository_root)
    connector = _connector(document)
    connector["projection_truth_statuses"] = ["authoritative"]

    with pytest.raises(
        ContractValidationError,
        match="AppGuardrail security evidence.*observed and inferred",
    ):
        validate_connector_catalog(document)
