"""Context Assertion projection receipt identity regressions."""

import json
from pathlib import Path

import pytest

from ea_core_foundation import ContractValidationError, validate_connector_catalog

_REQUIRED_RECEIPT_SEMANTICS = [
    "source_authority",
    "cloudevent_identity",
    "schema_version",
    "profile_id",
    "profile_version",
    "admission_version",
    "provenance",
]
_REQUIRED_CLOUDEVENT_IDENTITY_FIELDS = [
    "id",
    "source",
    "specversion",
    "type",
    "time",
    "subject",
    "dataschema",
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
    """Require authority, event, schema/profile, admission, and provenance identity."""

    document = _catalog(repository_root)
    connectors = _context_assertion_connectors(document)
    assert connectors
    for connector in connectors:
        assert connector["projection_receipt_semantics"] == _REQUIRED_RECEIPT_SEMANTICS
        assert connector["cloudevent_identity_fields"] == (
            _REQUIRED_CLOUDEVENT_IDENTITY_FIELDS
        )


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


def test_connector_catalog_rejects_projection_profile_identity_loss(
    repository_root,
) -> None:
    """Reject a receipt contract that keeps a version but drops its profile identity."""

    document = _catalog(repository_root)
    connector = next(
        connector
        for connector in _context_assertion_connectors(document)
        if connector["connector_name"] == "quarantine_sandbox_runtime"
    )
    connector["projection_receipt_semantics"] = [
        semantic
        for semantic in _REQUIRED_RECEIPT_SEMANTICS
        if semantic != "profile_id"
    ]

    with pytest.raises(
        ContractValidationError,
        match="projection receipt semantics",
    ):
        validate_connector_catalog(document)


def test_connector_catalog_rejects_cloud_event_identity_field_loss(
    repository_root,
) -> None:
    """Reject a Context Assertion connector that omits CloudEvent specversion."""

    document = _catalog(repository_root)
    connector = next(
        connector
        for connector in _context_assertion_connectors(document)
        if connector["connector_name"] == "quarantine_sandbox_runtime"
    )
    connector["cloudevent_identity_fields"] = [
        field
        for field in _REQUIRED_CLOUDEVENT_IDENTITY_FIELDS
        if field != "specversion"
    ]

    with pytest.raises(
        ContractValidationError,
        match="CloudEvent identity fields",
    ):
        validate_connector_catalog(document)
