"""Hostile regressions for every foreign-owner connector boundary branch."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from ea_core_foundation import ContractValidationError, validate_connector_catalog
from ea_core_foundation.cross_domain_evidence import (
    _connector_catalog_contracts as owner_contracts,
)
from ea_core_foundation.cross_domain_evidence.appguardrail_security_evidence import (
    validate_appguardrail_security_evidence,
)


def _catalog(repository_root: Path) -> dict:
    """Load the checked-in connector catalog as mutable hostile input."""

    return json.loads(
        (repository_root / "contracts/connectors/ecosystem.json").read_text(
            encoding="utf-8"
        )
    )


def _connector(document: dict, name: str) -> dict:
    """Return one named connector from a catalog document."""

    return next(
        connector
        for connector in document["connectors"]
        if connector["connector_name"] == name
    )


@pytest.mark.parametrize(
    ("connector_name", "field", "replacement", "message"),
    [
        (
            "contextual_orchestrator_proposal",
            "owner_repository",
            "ContextualWisdomLab/other-orchestrator",
            "Contextual Orchestrator proposal owner_repository",
        ),
        (
            "contextual_orchestrator_proposal",
            "direction_code",
            "inbound_evidence",
            "Contextual Orchestrator proposal direction_code",
        ),
        (
            "contextual_orchestrator_proposal",
            "exchange_kind",
            "cloudevents_json",
            "Contextual Orchestrator proposal must use the Context Assertion",
        ),
        (
            "appguardrail_security_evidence",
            "owner_repository",
            "ContextualWisdomLab/other-scanner",
            "AppGuardrail security evidence owner_repository",
        ),
        (
            "appguardrail_security_evidence",
            "direction_code",
            "inbound_projection",
            "AppGuardrail security evidence direction_code",
        ),
        (
            "appguardrail_security_evidence",
            "exchange_kind",
            "cloudevents_json",
            "AppGuardrail security evidence must use the Context Assertion",
        ),
    ],
)
def test_foreign_owner_boundary_drift_fails_closed(
    repository_root: Path,
    connector_name: str,
    field: str,
    replacement: str,
    message: str,
) -> None:
    """Owner, direction and exchange drift cannot pass the public validator."""

    document = _catalog(repository_root)
    _connector(document, connector_name)[field] = replacement

    with pytest.raises(ContractValidationError, match=message):
        validate_connector_catalog(document)


@pytest.mark.parametrize(
    ("connector_name", "message"),
    [
        (
            "contextual_orchestrator_proposal",
            "exactly one contextual_orchestrator_proposal",
        ),
        (
            "appguardrail_security_evidence",
            "exactly one AppGuardrail security evidence boundary",
        ),
    ],
)
def test_missing_foreign_owner_boundary_fails_closed(
    repository_root: Path,
    connector_name: str,
    message: str,
) -> None:
    """Removing a foreign evidence boundary cannot silently drop its ACL."""

    document = _catalog(repository_root)
    document["connectors"].remove(_connector(document, connector_name))

    with pytest.raises(ContractValidationError, match=message):
        validate_connector_catalog(document)


@pytest.mark.parametrize(
    ("connector_name", "validator", "message"),
    [
        (
            "contextual_orchestrator_proposal",
            owner_contracts._require_contextual_orchestrator_proposal_boundary,
            "Contextual Orchestrator proposal must remain outside EA Core",
        ),
        (
            "quarantine_sandbox_runtime",
            owner_contracts._require_quarantine_runtime_boundary,
            "quarantine runtime must remain outside EA Core",
        ),
        (
            "noema_projection",
            owner_contracts._require_noema_projection_boundary,
            "Noema projection must remain outside EA Core",
        ),
        (
            "wardnet_security_evidence",
            owner_contracts._require_wardnet_evidence_boundary,
            "Wardnet security evidence must remain outside EA Core",
        ),
        (
            "appguardrail_security_evidence",
            validate_appguardrail_security_evidence,
            "AppGuardrail security evidence must remain outside EA Core",
        ),
    ],
)
def test_owner_acl_rejects_ea_ownership_without_generic_guard(
    repository_root: Path,
    connector_name: str,
    validator,
    message: str,
) -> None:
    """Each owner ACL rejects EA ownership on its own (defense in depth).

    The generic catalog validator rejects ``ea_core_owns`` first, so these
    owner-specific checks are exercised directly to prove they would still
    fail closed if the generic guard changed.
    """

    document = deepcopy(_catalog(repository_root))
    _connector(document, connector_name)["ea_core_owns"] = True

    with pytest.raises(ContractValidationError, match=message):
        validator(document)
