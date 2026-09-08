"""Validate Context Fabric connector ownership and contract bindings."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from ._connector_catalog_contracts import (
    ContractValidationError,
    RepositoryReport,
    validate_connector_catalog as _validate_connector_catalog,
    validate_repository as _validate_repository,
)
from .appguardrail_security_evidence import validate_appguardrail_security_evidence

_ALLOWED_DIRECTION_CODES = frozenset(
    {
        "inbound_evidence",
        "inbound_identity",
        "inbound_policy",
        "inbound_projection",
        "inbound_proposal",
        "outbound_event",
        "shared_envelope",
    }
)


def _validate_direction_codes(document: Mapping[str, Any]) -> None:
    """Reject direction typos before they can bypass contract-bound validation."""

    for connector in document["connectors"]:
        direction_code = connector.get("direction_code")
        if direction_code not in _ALLOWED_DIRECTION_CODES:
            allowed = ", ".join(sorted(_ALLOWED_DIRECTION_CODES))
            raise ContractValidationError(
                "connector direction_code must be one of: " + allowed
            )


def validate_connector_catalog(document: Mapping[str, Any]) -> int:
    """Validate shared connector contracts plus foreign evidence boundaries."""

    connector_count = _validate_connector_catalog(document)
    _validate_direction_codes(document)
    validate_appguardrail_security_evidence(document)
    return connector_count


def validate_repository(repository_root: Path) -> RepositoryReport:
    """Validate repository artifacts through the complete connector boundary."""

    report = _validate_repository(repository_root)
    connector_path = repository_root / "contracts/connectors/ecosystem.json"
    connector_document = json.loads(connector_path.read_text(encoding="utf-8"))
    validate_connector_catalog(connector_document)
    return report
