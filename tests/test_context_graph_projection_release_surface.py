"""Release-surface regressions for Context Fabric projection dependencies."""

import json

_REQUIRED_PROJECTION_SCHEMA_IDS = {
    "https://schemas.contextualwisdomlab.org/context/"
    "canonical-authority-uri.v1.schema.json",
    "https://schemas.contextualwisdomlab.org/context/"
    "canonical-asset-uri.v1.schema.json",
    "https://schemas.contextualwisdomlab.org/context/"
    "cloudevent-envelope.v1.schema.json",
    "https://schemas.contextualwisdomlab.org/context/"
    "context-assertion.v1.schema.json",
    "https://schemas.contextualwisdomlab.org/context/"
    "context-membership.v1.schema.json",
    "https://schemas.contextualwisdomlab.org/context/"
    "truth-status.v1.schema.json",
    "https://schemas.contextualwisdomlab.org/context/"
    "bitemporal-interval.v1.schema.json",
    "https://schemas.contextualwisdomlab.org/context/"
    "provenance-reference.v1.schema.json",
}
_REQUIRED_PROJECTION_PROFILE_IDS = {
    "urn:cwl:conformance:cloudevent-semantics:v1",
    "urn:cwl:context-contracts:context-assertion-semantics:v1",
    "urn:cwl:context-contracts:context-assertion-event-semantics:v1",
    "urn:cwl:context-contracts:cwl-json-interoperability:v1",
    "urn:cwl:context-contracts:cwl-timestamp-profile:v1",
}
_REQUIRED_PROJECTION_RESOURCES = {
    "cwl_context_contracts.schemas:canonical-authority-uri.schema.json",
    "cwl_context_contracts.schemas:canonical-asset-uri.schema.json",
    "cwl_context_contracts.schemas:cloudevent-envelope.schema.json",
    "cwl_context_contracts.schemas:context-assertion.schema.json",
    "cwl_context_contracts.schemas:context-membership.schema.json",
    "cwl_context_contracts.schemas:truth-status.schema.json",
    "cwl_context_contracts.schemas:bitemporal-interval.schema.json",
    "cwl_context_contracts.schemas:provenance-reference.schema.json",
    "cwl_context_contracts.conformance:cloudevent-semantics.v1.json",
    "cwl_context_contracts.conformance:context-assertion-semantics.v1.json",
    "cwl_context_contracts.conformance:context-assertion-event-semantics.v1.json",
    "cwl_context_contracts.conformance:cwl-json-interoperability.v1.json",
    "cwl_context_contracts.conformance:cwl-timestamp-profile.v1.json",
    "cwl_context_contracts.contracts:context-fabric.asyncapi.json",
}


def test_context_projection_dependency_declares_complete_shared_release_surface(
    repository_root,
) -> None:
    """EA projections cannot claim semantics absent from the pinned release gate."""

    manifest = json.loads(
        (repository_root / "contracts/context-graph-dependency.json").read_text(
            encoding="utf-8"
        )
    )
    assert _REQUIRED_PROJECTION_SCHEMA_IDS <= set(manifest["required_schema_ids"])
    assert _REQUIRED_PROJECTION_PROFILE_IDS <= set(
        manifest["required_conformance_profile_ids"]
    )
    assert _REQUIRED_PROJECTION_RESOURCES <= set(
        manifest["required_package_resources"]
    )
