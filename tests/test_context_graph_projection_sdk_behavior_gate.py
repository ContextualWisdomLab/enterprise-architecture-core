"""Behavioral release-gate regressions for Context Assertion projection SDKs."""

from __future__ import annotations

import pytest

from scripts.verify_context_graph_release import (
    ContextGraphReleaseError,
    _EXPECTED_DISTRIBUTION,
    _EXPECTED_PROFILE_IDS,
    _EXPECTED_REPOSITORY,
    _EXPECTED_RESOURCES,
    _EXPECTED_SCHEMA_IDS,
    _EXPECTED_SDK_EXPORTS,
    _EXPECTED_SIGNER_WORKFLOW,
    _EXPECTED_SOURCE_MANIFEST_FORMAT,
    _EXPECTED_SOURCE_NEXT_ACTION,
    _REQUIRED_BEFORE_MERGE,
    _SBOM_NAME,
    verify_context_graph_release,
)

_RELEASE_VERSION = "0.2.0"
_RELEASE_SHA = "a" * 40


def _released_manifest() -> dict[str, object]:
    """Return one exact immutable-release fixture for the behavior-probe seam."""

    return {
        "contract_repository": _EXPECTED_REPOSITORY,
        "state": "immutable-release",
        "distribution_name": _EXPECTED_DISTRIBUTION,
        "release_version": _RELEASE_VERSION,
        "release_tag": f"v{_RELEASE_VERSION}",
        "release_commit_sha": _RELEASE_SHA,
        "approved_conformance_manifest": {},
        "approved_bundle_manifest": {},
        "release_source_manifest": {
            "manifest_format": _EXPECTED_SOURCE_MANIFEST_FORMAT,
            "distribution_name": _EXPECTED_DISTRIBUTION,
            "distribution_version": _RELEASE_VERSION,
            "release_tag": f"v{_RELEASE_VERSION}",
            "source_repository": _EXPECTED_REPOSITORY,
            "source_ref": "refs/heads/main",
            "source_commit_sha": _RELEASE_SHA,
            "signer_workflow": _EXPECTED_SIGNER_WORKFLOW,
            "algorithm": "sha256",
            "package_snapshot_sha256": "b" * 64,
            "artifacts": [
                {
                    "name": (
                        "cwl_context_contracts-0.2.0-py3-none-any.whl"
                    ),
                    "sha256": "c" * 64,
                },
                {
                    "name": "cwl_context_contracts-0.2.0.tar.gz",
                    "sha256": "d" * 64,
                },
                {"name": _SBOM_NAME, "sha256": "e" * 64},
            ],
            "next_action": _EXPECTED_SOURCE_NEXT_ACTION,
        },
        "required_schema_ids": list(_EXPECTED_SCHEMA_IDS),
        "required_conformance_profile_ids": list(_EXPECTED_PROFILE_IDS),
        "required_package_resources": list(_EXPECTED_RESOURCES),
        "required_sdk_exports": list(_EXPECTED_SDK_EXPORTS),
        "required_before_merge": _REQUIRED_BEFORE_MERGE,
    }


def test_context_graph_release_gate_requires_projection_sdk_behavior() -> None:
    """Names alone cannot prove that admission retains the CloudEvent receipt."""

    with pytest.raises(
        ContextGraphReleaseError,
        match="Context Assertion projection SDK behavior",
    ):
        verify_context_graph_release(
            _released_manifest(),
            version_reader=lambda _name: _RELEASE_VERSION,
            resource_exists=lambda _resource: True,
            sdk_export_exists=lambda _export: True,
            projection_sdk_verifier=lambda: False,
            bundle_verifier=lambda _manifest: True,
            release_admission_verifier=lambda _conformance, _bundle: True,
            source_attestation_verifier=lambda _source_manifest: True,
        )
