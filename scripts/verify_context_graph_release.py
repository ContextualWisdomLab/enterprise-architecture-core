"""Fail closed unless the consumed Context Graph contract is an immutable release."""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from collections.abc import Callable, Mapping
from importlib import import_module
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as distribution_version

# Python >=3.11 is the supported runtime contract; importlib.resources is stdlib.
# nosemgrep: python.lang.compatibility.python37.python37-compatibility-importlib2
from importlib.resources import files
from pathlib import Path

_EXPECTED_REPOSITORY = "ContextualWisdomLab/context-graph-contracts"
_EXPECTED_DISTRIBUTION = "cwl-context-contracts"
_EXPECTED_SOURCE_REF = "refs/heads/main"
_EXPECTED_SIGNER_WORKFLOW = (
    "ContextualWisdomLab/context-graph-contracts/.github/workflows/supply-chain.yml"
)
_EXPECTED_SOURCE_MANIFEST_FORMAT = "cwl-context-release-source-manifest/v1"
_EXPECTED_SOURCE_NEXT_ACTION = (
    "independently verify this manifest's artifact attestation against the same "
    "repository, protected ref, source SHA, and signer workflow before treating "
    "its source fields as release provenance"
)
_EXPECTED_SOURCE_FIELDS = frozenset(
    {
        "manifest_format",
        "distribution_name",
        "distribution_version",
        "release_tag",
        "source_repository",
        "source_ref",
        "source_commit_sha",
        "signer_workflow",
        "algorithm",
        "package_snapshot_sha256",
        "artifacts",
        "next_action",
    }
)
_EXPECTED_SCHEMA_IDS = (
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
_EXPECTED_PROFILE_IDS = (
    "urn:cwl:conformance:cloudevent-semantics:v1",
    "urn:cwl:context-contracts:context-assertion-semantics:v1",
    "urn:cwl:context-contracts:context-assertion-event-semantics:v1",
    "urn:cwl:context-contracts:cwl-json-interoperability:v1",
    "urn:cwl:context-contracts:cwl-timestamp-profile:v1",
    "urn:cwl:context-contracts:data-management-assessment-semantics:v1",
)
_EXPECTED_RESOURCES = (
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
_EXPECTED_SDK_EXPORTS = (
    "CONTEXT_ASSERTION_STRUCTURED_MEDIA_TYPE",
    "ContextAssertionAdmission",
    "admit_context_assertion_message",
)
_REQUIRED_BEFORE_MERGE = (
    "immutable released dependency containing every declared artifact"
)
_SOURCE_RECEIPT_ENV = "EA_CGC_SOURCE_ATTESTATION_RECEIPT"
_SOURCE_RECEIPT_FORMAT = "ea-cgc-source-attestation-verification/v1"
_VERSION_PATTERN = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
_COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_WHEEL_PATTERN = re.compile(
    r"^cwl_context_contracts-([0-9]+\.[0-9]+\.[0-9]+)-"
    r"[^-]+-[^-]+-[^-]+\.whl$"
)
_SDIST_PATTERN = re.compile(
    r"^cwl_context_contracts-([0-9]+\.[0-9]+\.[0-9]+)\.tar\.gz$"
)
_SBOM_NAME = "cwl-context-contracts.spdx.json"

VersionReader = Callable[[str], str]
ResourceProbe = Callable[[str], bool]
SdkExportProbe = Callable[[str], bool]
ProjectionSdkVerifier = Callable[[], bool]
BundleVerifier = Callable[[object], bool]
ReleaseAdmissionVerifier = Callable[[object, object], bool]
SourceAttestationVerifier = Callable[[Mapping[str, object]], bool]


class ContextGraphReleaseError(RuntimeError):
    """Raised when protected integration lacks exact immutable contract evidence."""


def _default_resource_exists(resource_specification: str) -> bool:
    """Return whether one declared resource exists in the installed distribution."""

    package_name, separator, relative_path = resource_specification.partition(":")
    if separator != ":" or not package_name or not relative_path:
        return False
    try:
        return files(package_name).joinpath(relative_path).is_file()
    except (ImportError, TypeError):
        return False


def _default_sdk_export_exists(export_name: str) -> bool:
    """Return whether the installed package exposes one declared public SDK symbol."""

    try:
        package = import_module("cwl_context_contracts")
        public_exports = getattr(package, "__all__")
    except Exception:
        return False
    return (
        isinstance(public_exports, list)
        and export_name in public_exports
        and hasattr(package, export_name)
    )


def _default_projection_sdk_verified() -> bool:
    """Verify that installed Context Assertion admission retains projection identity."""

    try:
        package = import_module("cwl_context_contracts")
        media_type = getattr(package, "CONTEXT_ASSERTION_STRUCTURED_MEDIA_TYPE")
        admission_type = getattr(package, "ContextAssertionAdmission")
        admit = getattr(package, "admit_context_assertion_message")
        profile = json.loads(
            files("cwl_context_contracts.conformance")
            .joinpath("context-assertion-event-semantics.v1.json")
            .read_text(encoding="utf-8")
        )
        valid_vectors = profile.get("valid_vectors")
        if not isinstance(valid_vectors, list) or not valid_vectors:
            return False
        vector = valid_vectors[0]
        if not isinstance(vector, Mapping):
            return False
        event = vector.get("value")
        if not isinstance(event, Mapping):
            return False
        admitted = admit(media_type, event)
        if not isinstance(admitted, admission_type):
            return False
        envelope_mapping = admitted.envelope.to_mapping()
        assertion_mapping = admitted.assertion.to_mapping()
    except Exception:
        return False

    return (
        media_type == "application/cloudevents+json"
        and envelope_mapping == event
        and assertion_mapping == event.get("data")
        and admitted.profile_id
        == "urn:cwl:context-contracts:context-assertion-event-semantics:v1"
        and admitted.profile_version == 1
        and admitted.admission_version == 1
    )


def _default_bundle_verified(approved_manifest: object) -> bool:
    """Verify approved complete bundle evidence using the installed provider SDK."""

    try:
        verifier_module = import_module(
            "cwl_context_contracts.contract_bundle_manifest_verifier"
        )
        verifier = verifier_module.verify_packaged_contract_bundle_manifest
        report = verifier(approved_manifest)
    except Exception:
        return False
    return getattr(report, "verified", False) is True


def _default_release_admitted(
    approved_conformance_manifest: object,
    approved_bundle_manifest: object,
) -> bool:
    """Execute provider semantic and bundle admission against installed bytes."""

    try:
        admission_module = import_module(
            "cwl_context_contracts.contract_release_admission"
        )
        evaluator = admission_module.evaluate_packaged_contract_release_admission
        report = evaluator(
            approved_conformance_manifest,
            approved_bundle_manifest,
        )
    except Exception:
        return False
    return getattr(report, "admitted", False) is True


def _source_manifest_sha256(source_manifest: Mapping[str, object]) -> str:
    """Return the digest of the deterministic bytes emitted by the provider CLI."""

    encoded = (json.dumps(source_manifest, sort_keys=True) + "\n").encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _default_source_attestation_verified(
    source_manifest: Mapping[str, object],
) -> bool:
    """Admit only a runtime-generated receipt bound to the exact manifest bytes."""

    receipt_path_text = os.environ.get(_SOURCE_RECEIPT_ENV)
    if not receipt_path_text:
        return False
    try:
        receipt = json.loads(Path(receipt_path_text).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    if not isinstance(receipt, Mapping):
        return False
    expected = {
        "verification_format": _SOURCE_RECEIPT_FORMAT,
        "verified": True,
        "manifest_sha256": _source_manifest_sha256(source_manifest),
        "source_repository": _EXPECTED_REPOSITORY,
        "source_ref": _EXPECTED_SOURCE_REF,
        "source_commit_sha": source_manifest.get("source_commit_sha"),
        "signer_workflow": _EXPECTED_SIGNER_WORKFLOW,
        "predicate_type": "https://slsa.dev/provenance/v1",
    }
    return dict(receipt) == expected


def _require_exact_list(
    manifest: Mapping[str, object],
    field_name: str,
    expected_values: tuple[str, ...],
) -> None:
    """Require one ordered manifest list to match the consumed artifact surface."""

    raw_values = manifest.get(field_name)
    if not isinstance(raw_values, list) or tuple(raw_values) != expected_values:
        raise ContextGraphReleaseError(
            f"{field_name} must name the exact consumed Context Graph artifacts"
        )


def _require_sha256(value: object) -> bool:
    """Return whether a value is one canonical lowercase SHA-256 digest."""

    return isinstance(value, str) and _SHA256_PATTERN.fullmatch(value) is not None


def _validate_release_source_manifest(
    source_manifest: Mapping[str, object],
    *,
    release_version: str,
    release_commit_sha: str,
) -> None:
    """Bind attested source evidence to this exact consumed release identity."""

    if set(source_manifest) != _EXPECTED_SOURCE_FIELDS:
        raise ContextGraphReleaseError("release-source manifest has unexpected fields")
    exact_values = {
        "manifest_format": _EXPECTED_SOURCE_MANIFEST_FORMAT,
        "distribution_name": _EXPECTED_DISTRIBUTION,
        "distribution_version": release_version,
        "release_tag": f"v{release_version}",
        "source_repository": _EXPECTED_REPOSITORY,
        "source_ref": _EXPECTED_SOURCE_REF,
        "source_commit_sha": release_commit_sha,
        "signer_workflow": _EXPECTED_SIGNER_WORKFLOW,
        "algorithm": "sha256",
        "next_action": _EXPECTED_SOURCE_NEXT_ACTION,
    }
    if any(source_manifest.get(field) != value for field, value in exact_values.items()):
        raise ContextGraphReleaseError(
            "release-source manifest does not bind the exact release identity"
        )
    if not _require_sha256(source_manifest.get("package_snapshot_sha256")):
        raise ContextGraphReleaseError("release-source manifest package digest is invalid")

    raw_artifacts = source_manifest.get("artifacts")
    if not isinstance(raw_artifacts, list) or len(raw_artifacts) != 3:
        raise ContextGraphReleaseError("release-source manifest artifact set is invalid")
    artifact_names: list[str] = []
    for artifact in raw_artifacts:
        if not isinstance(artifact, Mapping) or set(artifact) != {"name", "sha256"}:
            raise ContextGraphReleaseError(
                "release-source manifest artifact set is invalid"
            )
        name = artifact.get("name")
        digest = artifact.get("sha256")
        if not isinstance(name, str) or not _require_sha256(digest):
            raise ContextGraphReleaseError(
                "release-source manifest artifact set is invalid"
            )
        artifact_names.append(name)
    if len(set(artifact_names)) != len(artifact_names):
        raise ContextGraphReleaseError("release-source manifest artifact set is invalid")

    wheel_names = [name for name in artifact_names if name.endswith(".whl")]
    sdist_names = [name for name in artifact_names if name.endswith(".tar.gz")]
    if (
        len(wheel_names) != 1
        or len(sdist_names) != 1
        or artifact_names.count(_SBOM_NAME) != 1
    ):
        raise ContextGraphReleaseError("release-source manifest artifact set is invalid")
    wheel_match = _WHEEL_PATTERN.fullmatch(wheel_names[0])
    sdist_match = _SDIST_PATTERN.fullmatch(sdist_names[0])
    if (
        wheel_match is None
        or sdist_match is None
        or wheel_match.group(1) != release_version
        or sdist_match.group(1) != release_version
    ):
        raise ContextGraphReleaseError("release-source manifest artifact set is invalid")


def verify_context_graph_release(
    manifest: Mapping[str, object],
    *,
    version_reader: VersionReader = distribution_version,
    resource_exists: ResourceProbe = _default_resource_exists,
    sdk_export_exists: SdkExportProbe = _default_sdk_export_exists,
    projection_sdk_verifier: ProjectionSdkVerifier = _default_projection_sdk_verified,
    bundle_verifier: BundleVerifier = _default_bundle_verified,
    release_admission_verifier: ReleaseAdmissionVerifier = _default_release_admitted,
    source_attestation_verifier: SourceAttestationVerifier = (
        _default_source_attestation_verified
    ),
) -> str:
    """Verify installed, semantic, bundle, SDK, and attested source release evidence."""

    if manifest.get("contract_repository") != _EXPECTED_REPOSITORY:
        raise ContextGraphReleaseError(
            "contract_repository is not the Context Graph authority"
        )
    _require_exact_list(manifest, "required_schema_ids", _EXPECTED_SCHEMA_IDS)
    _require_exact_list(
        manifest,
        "required_conformance_profile_ids",
        _EXPECTED_PROFILE_IDS,
    )
    _require_exact_list(manifest, "required_package_resources", _EXPECTED_RESOURCES)
    _require_exact_list(manifest, "required_sdk_exports", _EXPECTED_SDK_EXPORTS)
    if manifest.get("required_before_merge") != _REQUIRED_BEFORE_MERGE:
        raise ContextGraphReleaseError("required_before_merge contract has drifted")
    if manifest.get("state") != "immutable-release":
        raise ContextGraphReleaseError(
            "Context Graph dependency state must be immutable-release before "
            "protected integration"
        )
    if manifest.get("distribution_name") != _EXPECTED_DISTRIBUTION:
        raise ContextGraphReleaseError(
            "distribution_name must be cwl-context-contracts"
        )

    release_version = manifest.get("release_version")
    if (
        not isinstance(release_version, str)
        or _VERSION_PATTERN.fullmatch(release_version) is None
    ):
        raise ContextGraphReleaseError(
            "release_version must be an exact semantic version"
        )
    if manifest.get("release_tag") != f"v{release_version}":
        raise ContextGraphReleaseError(
            "release_tag must exactly bind the declared release_version"
        )
    release_commit_sha = manifest.get("release_commit_sha")
    if (
        not isinstance(release_commit_sha, str)
        or _COMMIT_PATTERN.fullmatch(release_commit_sha) is None
    ):
        raise ContextGraphReleaseError(
            "release_commit_sha must be a lowercase 40-hex commit"
        )

    approved_conformance_manifest = manifest.get("approved_conformance_manifest")
    if not isinstance(approved_conformance_manifest, Mapping):
        raise ContextGraphReleaseError(
            "approved conformance manifest is required for semantic admission"
        )
    approved_bundle_manifest = manifest.get("approved_bundle_manifest")
    if not isinstance(approved_bundle_manifest, Mapping):
        raise ContextGraphReleaseError(
            "approved bundle manifest is required for immutable release evidence"
        )
    release_source_manifest = manifest.get("release_source_manifest")
    if not isinstance(release_source_manifest, Mapping):
        raise ContextGraphReleaseError(
            "attested release-source manifest is required for immutable provenance"
        )
    _validate_release_source_manifest(
        release_source_manifest,
        release_version=release_version,
        release_commit_sha=release_commit_sha,
    )

    try:
        installed_version = version_reader(_EXPECTED_DISTRIBUTION)
    except PackageNotFoundError as error:
        raise ContextGraphReleaseError(
            "cwl-context-contracts immutable release is not installed from "
            "the reviewed lock"
        ) from error
    except Exception as error:
        raise ContextGraphReleaseError(
            "installed Context Graph release version could not be verified"
        ) from error
    if installed_version != release_version:
        raise ContextGraphReleaseError(
            "installed release version does not match the declared immutable release"
        )

    for resource_specification in _EXPECTED_RESOURCES:
        if not resource_exists(resource_specification):
            raise ContextGraphReleaseError(
                "missing packaged resource from immutable release: "
                f"{resource_specification}"
            )
    for export_name in _EXPECTED_SDK_EXPORTS:
        if not sdk_export_exists(export_name):
            raise ContextGraphReleaseError(
                "missing packaged SDK export from immutable release: "
                f"{export_name}"
            )

    try:
        projection_sdk_verified = projection_sdk_verifier()
    except Exception as error:
        raise ContextGraphReleaseError(
            "Context Assertion projection SDK behavior could not be verified"
        ) from error
    if projection_sdk_verified is not True:
        raise ContextGraphReleaseError(
            "Context Assertion projection SDK behavior does not retain the "
            "admitted CloudEvent receipt"
        )

    try:
        bundle_verified = bundle_verifier(approved_bundle_manifest)
    except Exception as error:
        raise ContextGraphReleaseError(
            "approved bundle manifest could not be verified against the installed "
            "release"
        ) from error
    if bundle_verified is not True:
        raise ContextGraphReleaseError(
            "approved bundle manifest does not match the installed Context Graph "
            "release"
        )

    try:
        release_admitted = release_admission_verifier(
            approved_conformance_manifest,
            approved_bundle_manifest,
        )
    except Exception as error:
        raise ContextGraphReleaseError(
            "Context Graph conformance admission could not be executed"
        ) from error
    if release_admitted is not True:
        raise ContextGraphReleaseError(
            "Context Graph conformance admission did not admit the installed release"
        )

    try:
        source_verified = source_attestation_verifier(release_source_manifest)
    except Exception as error:
        raise ContextGraphReleaseError(
            "release-source attestation verification could not be executed"
        ) from error
    if source_verified is not True:
        raise ContextGraphReleaseError(
            "release-source attestation did not authenticate the declared source"
        )

    return release_commit_sha


def main() -> int:
    """Validate the dependency manifest for a protected integration job."""

    manifest_path = Path("contracts/context-graph-dependency.json")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if not isinstance(manifest, dict):
            raise ContextGraphReleaseError(
                "Context Graph dependency manifest must be an object"
            )
        release_commit_sha = verify_context_graph_release(manifest)
    except (OSError, json.JSONDecodeError, ContextGraphReleaseError) as error:
        print(f"Context Graph release gate failed: {error}", file=sys.stderr)
        return 1
    print(f"Context Graph release gate passed at {release_commit_sha}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
