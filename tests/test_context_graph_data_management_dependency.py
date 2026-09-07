"""Context Graph release-dependency regressions for data-management projection."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.verify_context_graph_release import (
    _EXPECTED_PROFILE_IDS,
    _EXPECTED_RESOURCES,
)

_SCHEMA_IDS = {
    "https://schemas.contextualwisdomlab.org/context/"
    "canonical-authority-uri.v1.schema.json",
    "https://schemas.contextualwisdomlab.org/context/"
    "canonical-asset-uri.v1.schema.json",
    "https://schemas.contextualwisdomlab.org/context/"
    "cloudevent-envelope.v1.schema.json",
    "https://schemas.contextualwisdomlab.org/context/"
    "data-management-assessment.v1.schema.json",
}
_ASSESSMENT_PROFILE_ID = (
    "urn:cwl:context-contracts:data-management-assessment-semantics:v1"
)
_CONTEXT_ASSERTION_MESSAGE_ADMISSION_PROFILE_ID = (
    "urn:cwl:context-contracts:context-assertion-message-admission:v1"
)
_CONTEXT_ASSERTION_MESSAGE_ADMISSION_RESOURCE = (
    "cwl_context_contracts.conformance:context-assertion-message-admission.v1.json"
)
_REQUIRED_RESOURCES = {
    "cwl_context_contracts.schemas:canonical-authority-uri.schema.json",
    "cwl_context_contracts.schemas:canonical-asset-uri.schema.json",
    "cwl_context_contracts.schemas:cloudevent-envelope.schema.json",
    "cwl_context_contracts.schemas:data-management-assessment.schema.json",
    "cwl_context_contracts.conformance:data-management-assessment-semantics.v1.json",
}


def test_data_management_projection_declares_release_artifacts(
    repository_root: Path,
) -> None:
    """The merge gate retains its domain artifacts as the shared release grows."""

    dependency_path = repository_root / "contracts/context-graph-dependency.json"
    document = json.loads(dependency_path.read_text(encoding="utf-8"))

    assert document["contract_repository"] == (
        "ContextualWisdomLab/context-graph-contracts"
    )
    assert document["state"] == "provisional-pr-head"
    assert document["distribution_name"] == "cwl-context-contracts"
    assert document["release_version"] is None
    assert document["release_tag"] is None
    assert document["release_commit_sha"] is None
    assert document["approved_bundle_manifest"] is None
    assert _SCHEMA_IDS <= set(document["required_schema_ids"])
    assert _ASSESSMENT_PROFILE_ID in document["required_conformance_profile_ids"]
    assert _REQUIRED_RESOURCES <= set(document["required_package_resources"])
    assert document["required_before_merge"] == (
        "immutable released dependency containing every declared artifact"
    )


def test_context_assertion_message_admission_is_release_required(
    repository_root: Path,
) -> None:
    """Do not project Context Assertions without the structured-message profile."""

    dependency_path = repository_root / "contracts/context-graph-dependency.json"
    document = json.loads(dependency_path.read_text(encoding="utf-8"))

    assert _CONTEXT_ASSERTION_MESSAGE_ADMISSION_PROFILE_ID in document[
        "required_conformance_profile_ids"
    ]
    assert _CONTEXT_ASSERTION_MESSAGE_ADMISSION_RESOURCE in document[
        "required_package_resources"
    ]
    assert _CONTEXT_ASSERTION_MESSAGE_ADMISSION_PROFILE_ID in _EXPECTED_PROFILE_IDS
    assert _CONTEXT_ASSERTION_MESSAGE_ADMISSION_RESOURCE in _EXPECTED_RESOURCES
