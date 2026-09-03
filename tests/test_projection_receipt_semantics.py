"""Context Assertion projection receipt identity regressions."""

import json
from pathlib import Path

import pytest

from ea_core_foundation import ContractValidationError, validate_connector_catalog

_REQUIRED_RECEIPT_SEMANTICS = [
    "source_authority",
    "cloudevent_identity",
    "schema_version",
    "profile_version",
    "admission_version",
    "provenance",
]


def _catalog(repository_root: Path) -> dict:
    """Load the checked-in connector catalog as mutable acceptance input."""

    return json.loads(
        (repository_root / "contracts/connectors/ecosystem.json").read_text(
            encoding="utf-8"
        )
    )


def _context_assertion_connectors(document: dict) -> list[dict]:
    """Return connectors that consume the Context Assertion CloudEvent contract."""

    return [
        connector
        for connector in document["connectors"]
        if connector.get("exchange_kind") == "context_assertion_cloudevent"
    ]


def test_context_assertion_projections_retain_receipt_identity(repository_root) -> None:
    """Require authority, event, version, and provenance identity on projections."""

    document = _catalog(repository_root)
    connectors = _context_assertion_connectors(document)
    assert connectors
    for connector in connectors:
        assert connector["projection_receipt_semantics"] == _REQUIRED_RECEIPT_SEMANTICS


def test_connector_catalog_rejects_projection_receipt_identity_loss(
    repository_root,
) -> None:
    """Reject a Context Assertion connector that drops admitted message identity."""

    document = _catalog(repository_root)
    connector = next(
        connector
        for connector in _context_assertion_connectors(document)
        if connector["connector_name"] == "quarantine_sandbox_runtime"
    )
    connector["projection_receipt_semantics"] = [
        semantic
        for semantic in _REQUIRED_RECEIPT_SEMANTICS
        if semantic != "cloudevent_identity"
    ]

    with pytest.raises(
        ContractValidationError,
        match="projection receipt semantics",
    ):
        validate_connector_catalog(document)
