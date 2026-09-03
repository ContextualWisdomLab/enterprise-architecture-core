"""Noema Context Fabric connector ownership regressions."""

from __future__ import annotations

import json
from copy import deepcopy

import pytest

from ea_core_foundation import ContractValidationError, validate_connector_catalog

_CONNECTOR_NAME = "noema_projection"
_OWNER_REPOSITORY = "ContextualWisdomLab/noema"
_PROJECTION_SCOPE = [
    "runtime_identity",
    "service_identity",
    "api_identity",
    "worker_identity",
    "workflow_runtime_capability_identity",
    "database_technology",
    "queue_technology",
    "object_storage_technology",
    "runtime_technology",
    "technology_provider",
    "technology_version",
    "lifecycle",
    "ownership",
    "architecture_risk_context",
    "remediation",
    "transformation",
]
_FORBIDDEN_AUTHORITATIVE_FACTS = [
    "agent_task",
    "agent_result",
    "agent_reasoning",
    "tool_payload",
    "workflow_execution_state",
    "approval_decision",
    "checkpoint_content",
    "prompt_content",
    "model_output",
    "user_business_data",
    "malware_verdict",
    "security_risk_score",
]
_PROHIBITED_INTEGRATIONS = [
    "direct_database_access",
    "source_copy",
]


def _catalog(repository_root) -> dict:
    """Load the executable connector inventory as mutable acceptance input."""

    return json.loads(
        (repository_root / "contracts/connectors/ecosystem.json").read_text(
            encoding="utf-8"
        )
    )


def _connector(document: dict) -> dict:
    """Return the canonical Noema projection boundary."""

    return next(
        connector
        for connector in document["connectors"]
        if connector.get("connector_name") == _CONNECTOR_NAME
    )


def test_noema_projection_connector_preserves_owner_and_admission_boundary(
    repository_root,
) -> None:
    """EA must represent Noema deployables without absorbing Agent Runtime truth."""

    document = _catalog(repository_root)
    connector = _connector(document)

    assert connector["owner_repository"] == _OWNER_REPOSITORY
    assert connector["direction_code"] == "inbound_projection"
    assert connector["exchange_kind"] == "context_assertion_cloudevent"
    assert connector["ea_core_owns"] is False
    assert (
        connector["context_contract_dependency"]
        == "contracts/context-graph-dependency.json"
    )
    assert connector["preserved_semantics"] == [
        "canonical_reference",
        "source_reference",
        "truth_status",
        "effective_time",
        "system_time",
        "provenance",
    ]
    assert connector["projection_receipt_semantics"] == [
        "source_authority",
        "cloudevent_identity",
        "schema_version",
        "profile_version",
        "admission_version",
        "provenance",
    ]
    assert connector["cloudevent_identity_fields"] == [
        "id",
        "source",
        "specversion",
        "type",
        "time",
        "subject",
        "dataschema",
    ]
    assert connector["architecture_projection_scope"] == _PROJECTION_SCOPE
    assert connector["forbidden_authoritative_facts"] == _FORBIDDEN_AUTHORITATIVE_FACTS
    assert connector["prohibited_integrations"] == _PROHIBITED_INTEGRATIONS
    assert validate_connector_catalog(document) == len(document["connectors"])


def test_noema_projection_is_required_exactly_once(repository_root) -> None:
    """Reject omitted, duplicated, or shadow-owner Noema projection boundaries."""

    document = _catalog(repository_root)
    connector = deepcopy(_connector(document))
    document["connectors"] = [
        item
        for item in document["connectors"]
        if item.get("connector_name") != _CONNECTOR_NAME
    ]
    with pytest.raises(
        ContractValidationError,
        match="exactly one noema_projection",
    ):
        validate_connector_catalog(document)

    document = _catalog(repository_root)
    duplicate = deepcopy(connector)
    duplicate["connector_name"] = "noema_runtime_projection"
    document["connectors"].append(duplicate)
    with pytest.raises(
        ContractValidationError,
        match="exactly one Noema owner boundary",
    ):
        validate_connector_catalog(document)


@pytest.mark.parametrize(
    ("field", "replacement", "message"),
    [
        ("owner_repository", "ContextualWisdomLab/contextual-orchestrator", "owner_repository"),
        ("direction_code", "inbound_proposal", "direction_code"),
        ("exchange_kind", "cloudevents_json", "exchange_kind"),
        (
            "architecture_projection_scope",
            ["agent_task"],
            "architecture projection scope",
        ),
        (
            "forbidden_authoritative_facts",
            ["agent_task"],
            "forbidden as authoritative EA facts",
        ),
        ("prohibited_integrations", ["direct_database_access"], "source copy"),
    ],
)
def test_noema_projection_boundary_fields_fail_closed(
    repository_root,
    field,
    replacement,
    message,
) -> None:
    """Reject ownership, scope, and anti-coupling drift at the Noema ACL."""

    document = _catalog(repository_root)
    _connector(document)[field] = replacement

    with pytest.raises(ContractValidationError, match=message):
        validate_connector_catalog(document)
