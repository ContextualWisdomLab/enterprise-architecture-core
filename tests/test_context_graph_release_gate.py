"""Protected-integration gate regressions for Context Graph release evidence."""

from __future__ import annotations

from copy import deepcopy

import pytest

from scripts.verify_context_graph_release import (
    ContextGraphReleaseError,
    verify_context_graph_release,
)

_SCHEMA_IDS = (
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
    "https://schemas.contextualwisdomlab.org/context/"
    "data-management-assessment.v1.schema.json",
)
_PROFILE_IDS = (
    "urn:cwl:conformance:cloudevent-semantics:v1",
    "urn:cwl:context-contracts:context-assertion-semantics:v1",
    "urn:cwl:context-contracts:context-assertion-event-semantics:v1",
    "urn:cwl:context-contracts:cwl-json-interoperability:v1",
    "urn:cwl:context-contracts:cwl-timestamp-profile:v1",
    "urn:cwl:context-contracts:data-management-assessment-semantics:v1",
)
_REQUIRED_RESOURCES = (
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
    "cwl_context_contracts.schemas:data-management-assessment.schema.json",
    "cwl_context_contracts.conformance:data-management-assessment-semantics.v1.json",
)
_APPROVED_BUNDLE_MANIFEST = {
    "manifest_format": "cwl-context-bundle-manifest/v1",
    "distribution_name": "cwl-context-contracts",
    "distribution_version": "0.2.0",
    "algorithm": "sha256",
    "resource_count": 1,
    "resources": [
        {
            "resource_path": "schemas/data-management-assessment.schema.json",
            "sha256": "b" * 64,
        }
    ],
}


def _released_manifest() -> dict[str, object]:
    """Return one immutable-release fixture matching the consumed contract surface."""

    return {
        "contract_repository": "ContextualWisdomLab/context-graph-contracts",
        "state": "immutable-release",
        "distribution_name": "cwl-context-contracts",
        "release_version": "0.2.0",
        "release_tag": "v0.2.0",
        "release_commit_sha": "a" * 40,
        "approved_bundle_manifest": deepcopy(_APPROVED_BUNDLE_MANIFEST),
        "required_schema_ids": list(_SCHEMA_IDS),
        "required_conformance_profile_ids": list(_PROFILE_IDS),
        "required_package_resources": list(_REQUIRED_RESOURCES),
        "required_before_merge": (
            "immutable released dependency containing every declared artifact"
        ),
    }


def _bundle_verified(_approved_manifest: object) -> bool:
    """Return deterministic installed-bundle agreement for focused gate tests."""

    return True


def test_provisional_context_graph_head_cannot_satisfy_release_gate() -> None:
    """An open PR head is never accepted as protected-integration provenance."""

    manifest = _released_manifest()
    manifest["state"] = "provisional-pr-head"
    manifest["release_version"] = None
    manifest["release_tag"] = None
    manifest["release_commit_sha"] = None
    manifest["approved_bundle_manifest"] = None

    with pytest.raises(ContextGraphReleaseError, match="immutable-release"):
        verify_context_graph_release(
            manifest,
            version_reader=lambda _name: "0.2.0",
            resource_exists=lambda _resource: True,
            bundle_verifier=_bundle_verified,
        )


def test_context_graph_release_gate_rejects_unlocked_distribution_version() -> None:
    """A different installed distribution cannot impersonate the declared release."""

    with pytest.raises(ContextGraphReleaseError, match="installed release version"):
        verify_context_graph_release(
            _released_manifest(),
            version_reader=lambda _name: "0.1.0",
            resource_exists=lambda _resource: True,
            bundle_verifier=_bundle_verified,
        )


def test_context_graph_release_gate_requires_every_consumed_packaged_artifact() -> None:
    """Require every consumed schema/profile to exist in the released wheel."""

    manifest = _released_manifest()
    missing_resource = _REQUIRED_RESOURCES[-1]

    with pytest.raises(ContextGraphReleaseError, match="missing packaged resource"):
        verify_context_graph_release(
            manifest,
            version_reader=lambda _name: "0.2.0",
            resource_exists=lambda resource: resource != missing_resource,
            bundle_verifier=_bundle_verified,
        )


def test_context_graph_release_gate_rejects_release_identity_drift() -> None:
    """Release tag and commit evidence must remain canonical and immutable-looking."""

    manifest = deepcopy(_released_manifest())
    manifest["release_commit_sha"] = "not-a-commit"

    with pytest.raises(ContextGraphReleaseError, match="release_commit_sha"):
        verify_context_graph_release(
            manifest,
            version_reader=lambda _name: "0.2.0",
            resource_exists=lambda _resource: True,
            bundle_verifier=_bundle_verified,
        )


def test_context_graph_release_gate_requires_approved_bundle_manifest() -> None:
    """A release identity without approved complete bundle evidence is insufficient."""

    manifest = _released_manifest()
    manifest["approved_bundle_manifest"] = None

    with pytest.raises(ContextGraphReleaseError, match="approved bundle manifest"):
        verify_context_graph_release(
            manifest,
            version_reader=lambda _name: "0.2.0",
            resource_exists=lambda _resource: True,
            bundle_verifier=_bundle_verified,
        )


def test_context_graph_release_gate_rejects_installed_bundle_digest_drift() -> None:
    """Installed package bytes must match the independently approved bundle evidence."""

    with pytest.raises(ContextGraphReleaseError, match="approved bundle manifest"):
        verify_context_graph_release(
            _released_manifest(),
            version_reader=lambda _name: "0.2.0",
            resource_exists=lambda _resource: True,
            bundle_verifier=lambda _manifest: False,
        )


def test_context_graph_release_gate_accepts_exact_locked_artifact_set() -> None:
    """Accept exact release identity, installed version, resources, and bundle bytes."""

    assert (
        verify_context_graph_release(
            _released_manifest(),
            version_reader=lambda _name: "0.2.0",
            resource_exists=lambda _resource: True,
            bundle_verifier=_bundle_verified,
        )
        == "a" * 40
    )
