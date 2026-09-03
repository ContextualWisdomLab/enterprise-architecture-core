"""Noema Context Fabric connector ownership regressions."""

from __future__ import annotations

import json


def test_noema_projection_connector_preserves_owner_and_admission_boundary(
    repository_root,
) -> None:
    """EA must represent Noema deployables without absorbing Agent Runtime truth."""

    document = json.loads(
        (repository_root / "contracts/connectors/ecosystem.json").read_text(
            encoding="utf-8"
        )
    )
    connectors = {
        connector["connector_name"]: connector for connector in document["connectors"]
    }
    connector = connectors["noema_projection"]

    assert connector["owner_repository"] == "ContextualWisdomLab/noema"
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
    assert connector["architecture_projection_scope"] == [
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
    assert connector["forbidden_authoritative_facts"] == [
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
    assert connector["prohibited_integrations"] == [
        "direct_database_access",
        "source_copy",
    ]
