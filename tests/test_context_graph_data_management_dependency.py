"""Context Graph release-dependency regressions for data-management projection."""

from __future__ import annotations

import json
from pathlib import Path

_ASSESSMENT_SCHEMA_ID = (
    "https://schemas.contextualwisdomlab.org/context/"
    "data-management-assessment.v1.schema.json"
)
_ASSESSMENT_PROFILE_ID = (
    "urn:cwl:context-contracts:data-management-assessment-semantics:v1"
)


def test_data_management_projection_declares_release_artifacts(
    repository_root: Path,
) -> None:
    """The merge gate names the exact assessment grammar it actually consumes."""

    dependency_path = repository_root / "contracts/context-graph-dependency.json"
    document = json.loads(dependency_path.read_text(encoding="utf-8"))

    assert document == {
        "contract_repository": "ContextualWisdomLab/context-graph-contracts",
        "state": "provisional-pr-head",
        "required_schema_ids": [
            "https://schemas.contextualwisdomlab.org/context/canonical-authority-uri.v1.schema.json",
            "https://schemas.contextualwisdomlab.org/context/canonical-asset-uri.v1.schema.json",
            "https://schemas.contextualwisdomlab.org/context/cloudevent-envelope.v1.schema.json",
            _ASSESSMENT_SCHEMA_ID,
        ],
        "required_conformance_profile_ids": [_ASSESSMENT_PROFILE_ID],
        "required_before_merge": "immutable released dependency containing every declared artifact",
    }
