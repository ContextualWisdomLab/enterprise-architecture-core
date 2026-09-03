"""Release-source and conformance admission regressions for Context Graph."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from scripts.verify_context_graph_release import (
    ContextGraphReleaseError,
    verify_context_graph_release,
)

_RELEASE_SHA = "a" * 40


def _released_manifest() -> dict[str, object]:
    """Promote the checked-in provisional dependency to a deterministic fixture."""

    manifest = json.loads(
        Path("contracts/context-graph-dependency.json").read_text(encoding="utf-8")
    )
    manifest.update(
        {
            "state": "immutable-release",
            "release_version": "0.2.0",
            "release_tag": "v0.2.0",
            "release_commit_sha": _RELEASE_SHA,
            "approved_conformance_manifest": {
                "manifest_format": "cwl-context-conformance-manifest/v1",
                "distribution_name": "cwl-context-contracts",
                "distribution_version": "0.2.0",
                "algorithm": "sha256",
                "profile_count": 0,
                "profiles": [],
            },
            "approved_bundle_manifest": {
                "manifest_format": "cwl-context-bundle-manifest/v1",
                "distribution_name": "cwl-context-contracts",
                "distribution_version": "0.2.0",
                "algorithm": "sha256",
                "resource_count": 0,
                "resources": [],
            },
            "release_source_manifest": {
                "manifest_format": "cwl-context-release-source-manifest/v1",
                "distribution_name": "cwl-context-contracts",
                "distribution_version": "0.2.0",
                "release_tag": "v0.2.0",
                "source_repository": "ContextualWisdomLab/context-graph-contracts",
                "source_ref": "refs/heads/main",
                "source_commit_sha": _RELEASE_SHA,
                "signer_workflow": (
                    "ContextualWisdomLab/context-graph-contracts/"
                    ".github/workflows/supply-chain.yml"
                ),
                "algorithm": "sha256",
                "package_snapshot_sha256": "b" * 64,
                "artifacts": [
                    {
                        "name": "cwl_context_contracts-0.2.0-py3-none-any.whl",
                        "sha256": "c" * 64,
                    },
                    {
                        "name": "cwl_context_contracts-0.2.0.tar.gz",
                        "sha256": "d" * 64,
                    },
                    {
                        "name": "cwl-context-contracts.spdx.json",
                        "sha256": "e" * 64,
                    },
                ],
                "next_action": (
                    "independently verify this manifest's artifact attestation against "
                    "the same repository, protected ref, source SHA, and signer workflow "
                    "before treating its source fields as release provenance"
                ),
            },
        }
    )
    return manifest


def _verify_release(manifest: dict[str, object], **overrides) -> str:
    """Run the release gate with deterministic installed-package seams."""

    arguments = {
        "version_reader": lambda _name: "0.2.0",
        "resource_exists": lambda _resource: True,
        "release_admission_verifier": lambda _conformance, _bundle: True,
        "source_attestation_verifier": lambda _source_manifest: True,
    }
    arguments.update(overrides)
    return verify_context_graph_release(manifest, **arguments)


def test_release_requires_semantic_conformance_admission_evidence() -> None:
    """Bundle bytes alone cannot substitute for executed semantic admission."""

    manifest = _released_manifest()
    manifest["approved_conformance_manifest"] = None
    with pytest.raises(ContextGraphReleaseError, match="conformance manifest"):
        _verify_release(manifest)

    with pytest.raises(ContextGraphReleaseError, match="conformance admission"):
        _verify_release(
            _released_manifest(),
            release_admission_verifier=lambda _conformance, _bundle: False,
        )


def test_release_requires_attested_source_manifest_not_self_asserted_sha() -> None:
    """A syntactically valid commit SHA is insufficient source provenance."""

    manifest = _released_manifest()
    manifest["release_source_manifest"] = None
    with pytest.raises(ContextGraphReleaseError, match="release-source manifest"):
        _verify_release(manifest)

    with pytest.raises(ContextGraphReleaseError, match="attestation"):
        _verify_release(
            _released_manifest(),
            source_attestation_verifier=lambda _source_manifest: False,
        )


def test_release_source_manifest_must_bind_exact_release_identity() -> None:
    """Attested evidence must name this exact version, tag, source, and signer."""

    field_replacements = {
        "distribution_version": "0.3.0",
        "release_tag": "v0.3.0",
        "source_repository": "ContextualWisdomLab/other",
        "source_ref": "refs/heads/develop",
        "source_commit_sha": "f" * 40,
        "signer_workflow": "ContextualWisdomLab/other/.github/workflows/ci.yml",
    }
    for field, replacement in field_replacements.items():
        manifest = _released_manifest()
        source_manifest = deepcopy(manifest["release_source_manifest"])
        assert isinstance(source_manifest, dict)
        source_manifest[field] = replacement
        manifest["release_source_manifest"] = source_manifest
        with pytest.raises(ContextGraphReleaseError, match="release-source manifest"):
            _verify_release(manifest)


def test_exact_conformance_and_attested_source_evidence_admit_release() -> None:
    """Accept only when semantic, bundle, source, and installed identities agree."""

    assert _verify_release(_released_manifest()) == _RELEASE_SHA
