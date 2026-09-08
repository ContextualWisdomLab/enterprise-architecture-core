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
_REQUIRED_SDK_EXPORTS = (
    "CONTEXT_ASSERTION_STRUCTURED_MEDIA_TYPE",
    "ContextAssertionAdmission",
    "admit_context_assertion_message",
)
_APPROVED_CONFORMANCE_MANIFEST = {
    "manifest_format": "cwl-context-conformance-manifest/v1",
    "distribution_name": "cwl-context-contracts",
    "distribution_version": "0.2.0",
    "algorithm": "sha256",
    "profile_count": 0,
    "profiles": [],
}
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
_RELEASE_SOURCE_MANIFEST = {
    "manifest_format": "cwl-context-release-source-manifest/v1",
    "distribution_name": "cwl-context-contracts",
    "distribution_version": "0.2.0",
    "release_tag": "v0.2.0",
    "source_repository": "ContextualWisdomLab/context-graph-contracts",
    "source_ref": "refs/heads/main",
    "source_commit_sha": "a" * 40,
    "signer_workflow": (
        "ContextualWisdomLab/context-graph-contracts/"
        ".github/workflows/supply-chain.yml"
    ),
    "algorithm": "sha256",
    "package_snapshot_sha256": "c" * 64,
    "artifacts": [
        {
            "name": "cwl_context_contracts-0.2.0-py3-none-any.whl",
            "sha256": "d" * 64,
        },
        {
            "name": "cwl_context_contracts-0.2.0.tar.gz",
            "sha256": "e" * 64,
        },
        {"name": "cwl-context-contracts.spdx.json", "sha256": "f" * 64},
    ],
    "next_action": (
        "independently verify this manifest's artifact attestation against the same "
        "repository, protected ref, source SHA, and signer workflow before treating "
        "its source fields as release provenance"
    ),
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
        "approved_conformance_manifest": deepcopy(_APPROVED_CONFORMANCE_MANIFEST),
        "approved_bundle_manifest": deepcopy(_APPROVED_BUNDLE_MANIFEST),
        "release_source_manifest": deepcopy(_RELEASE_SOURCE_MANIFEST),
        "required_schema_ids": list(_SCHEMA_IDS),
        "required_conformance_profile_ids": list(_PROFILE_IDS),
        "required_package_resources": list(_REQUIRED_RESOURCES),
        "required_sdk_exports": list(_REQUIRED_SDK_EXPORTS),
        "required_before_merge": (
            "immutable released dependency containing every declared artifact"
        ),
    }


def _bundle_verified(_approved_manifest: object) -> bool:
    """Return deterministic installed-bundle agreement for focused gate tests."""

    return True


def _verify(manifest: dict[str, object], **overrides) -> str:
    """Run the release gate with positive semantic/source seams by default."""

    arguments = {
        "version_reader": lambda _name: "0.2.0",
        "resource_exists": lambda _resource: True,
        "sdk_export_exists": lambda _export: True,
        "projection_sdk_verifier": lambda: True,
        "bundle_verifier": _bundle_verified,
        "release_admission_verifier": lambda _conformance, _bundle: True,
        "source_attestation_verifier": lambda _source_manifest: True,
    }
    arguments.update(overrides)
    return verify_context_graph_release(manifest, **arguments)


def test_provisional_context_graph_head_cannot_satisfy_release_gate() -> None:
    """An open PR head is never accepted as protected-integration provenance."""

    manifest = _released_manifest()
    manifest["state"] = "provisional-pr-head"
    manifest["release_version"] = None
    manifest["release_tag"] = None
    manifest["release_commit_sha"] = None
    manifest["approved_conformance_manifest"] = None
    manifest["approved_bundle_manifest"] = None
    manifest["release_source_manifest"] = None

    with pytest.raises(ContextGraphReleaseError, match="immutable-release"):
        _verify(manifest)


def test_context_graph_release_gate_rejects_unlocked_distribution_version() -> None:
    """A different installed distribution cannot impersonate the declared release."""

    with pytest.raises(ContextGraphReleaseError, match="installed release version"):
        _verify(_released_manifest(), version_reader=lambda _name: "0.1.0")


def test_context_graph_release_gate_requires_every_consumed_packaged_artifact() -> None:
    """Require every consumed schema/profile to exist in the released wheel."""

    manifest = _released_manifest()
    missing_resource = _REQUIRED_RESOURCES[-1]

    with pytest.raises(ContextGraphReleaseError, match="missing packaged resource"):
        _verify(
            manifest,
            resource_exists=lambda resource: resource != missing_resource,
        )


def test_context_graph_release_gate_requires_exact_installed_sdk_surface() -> None:
    """Reject manifest drift or an installed package missing an advertised SDK export."""

    manifest = _released_manifest()
    manifest["required_sdk_exports"] = ["admit_context_assertion_message"]
    with pytest.raises(ContextGraphReleaseError, match="required_sdk_exports"):
        _verify(manifest)

    with pytest.raises(ContextGraphReleaseError, match="missing packaged SDK export"):
        _verify(
            _released_manifest(),
            sdk_export_exists=lambda export: export != "ContextAssertionAdmission",
        )


def test_context_graph_release_gate_rejects_release_identity_drift() -> None:
    """Release tag and commit evidence must remain canonical and immutable-looking."""

    manifest = deepcopy(_released_manifest())
    manifest["release_commit_sha"] = "not-a-commit"

    with pytest.raises(ContextGraphReleaseError, match="release_commit_sha"):
        _verify(manifest)


def test_context_graph_release_gate_requires_approved_bundle_manifest() -> None:
    """A release identity without approved complete bundle evidence is insufficient."""

    manifest = _released_manifest()
    manifest["approved_bundle_manifest"] = None

    with pytest.raises(ContextGraphReleaseError, match="approved bundle manifest"):
        _verify(manifest)


def test_context_graph_release_gate_rejects_installed_bundle_digest_drift() -> None:
    """Installed package bytes must match the independently approved bundle evidence."""

    with pytest.raises(ContextGraphReleaseError, match="approved bundle manifest"):
        _verify(_released_manifest(), bundle_verifier=lambda _manifest: False)


def test_context_graph_release_gate_accepts_exact_locked_artifact_set() -> None:
    """Accept exact release identity, semantic admission, bundle, and source proof."""

    assert _verify(_released_manifest()) == "a" * 40
