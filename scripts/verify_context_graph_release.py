"""Fail closed unless the consumed Context Graph contract is an immutable release."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Callable, Mapping
from importlib import import_module
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as distribution_version

# Python >=3.11 is the supported runtime contract; importlib.resources is stdlib.
from importlib.resources import files  # nosemgrep
from pathlib import Path

_EXPECTED_REPOSITORY = "ContextualWisdomLab/context-graph-contracts"
_EXPECTED_DISTRIBUTION = "cwl-context-contracts"
_EXPECTED_SCHEMA_IDS = (
    "https://schemas.contextualwisdomlab.org/context/"
    "canonical-authority-uri.v1.schema.json",
    "https://schemas.contextualwisdomlab.org/context/"
    "canonical-asset-uri.v1.schema.json",
    "https://schemas.contextualwisdomlab.org/context/"
    "cloudevent-envelope.v1.schema.json",
    "https://schemas.contextualwisdomlab.org/context/"
    "data-management-assessment.v1.schema.json",
)
_EXPECTED_PROFILE_IDS = (
    "urn:cwl:context-contracts:data-management-assessment-semantics:v1",
)
_EXPECTED_RESOURCES = (
    "cwl_context_contracts.schemas:canonical-authority-uri.schema.json",
    "cwl_context_contracts.schemas:canonical-asset-uri.schema.json",
    "cwl_context_contracts.schemas:cloudevent-envelope.schema.json",
    "cwl_context_contracts.schemas:data-management-assessment.schema.json",
    "cwl_context_contracts.conformance:data-management-assessment-semantics.v1.json",
)
_REQUIRED_BEFORE_MERGE = (
    "immutable released dependency containing every declared artifact"
)
_VERSION_PATTERN = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
_COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")

VersionReader = Callable[[str], str]
ResourceProbe = Callable[[str], bool]
BundleVerifier = Callable[[object], bool]


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


def verify_context_graph_release(
    manifest: Mapping[str, object],
    *,
    version_reader: VersionReader = distribution_version,
    resource_exists: ResourceProbe = _default_resource_exists,
    bundle_verifier: BundleVerifier = _default_bundle_verified,
) -> str:
    """Verify exact released identity and packaged resources; return source SHA."""

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

    approved_bundle_manifest = manifest.get("approved_bundle_manifest")
    if not isinstance(approved_bundle_manifest, Mapping):
        raise ContextGraphReleaseError(
            "approved bundle manifest is required for immutable release evidence"
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
