"""Behavioral release-gate regressions for Context Assertion projection SDKs."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

import scripts.verify_context_graph_release as release_verifier
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


@pytest.mark.parametrize(
    ("message_profile_id", "message_profile_version"),
    [
        ("urn:cwl:context-contracts:context-assertion-message-admission:v2", 1),
        ("urn:cwl:context-contracts:context-assertion-message-admission:v1", 2),
    ],
)
def test_default_projection_sdk_probe_rejects_message_profile_receipt_drift(
    monkeypatch: pytest.MonkeyPatch,
    message_profile_id: str,
    message_profile_version: int,
) -> None:
    """A release cannot pass while its admitted message-profile receipt has drifted."""

    event = {"data": {"assertion": "fixture"}}

    class Admission:
        """Minimal installed-provider receipt used to exercise the consumer probe."""

        def __init__(self) -> None:
            self.envelope = SimpleNamespace(to_mapping=lambda: event)
            self.assertion = SimpleNamespace(to_mapping=lambda: event["data"])
            self.schema_version = 1
            self.profile_id = (
                "urn:cwl:context-contracts:context-assertion-event-semantics:v1"
            )
            self.profile_version = 1
            self.message_profile_id = message_profile_id
            self.message_profile_version = message_profile_version
            self.admission_version = 1

    package = SimpleNamespace(
        CONTEXT_ASSERTION_STRUCTURED_MEDIA_TYPE="application/cloudevents+json",
        ContextAssertionAdmission=Admission,
        admit_context_assertion_message=lambda _media_type, _event: Admission(),
    )
    profile_resource = SimpleNamespace(
        read_text=lambda **_kwargs: json.dumps(
            {"valid_vectors": [{"value": event}]}
        )
    )
    resource_root = SimpleNamespace(joinpath=lambda _name: profile_resource)

    monkeypatch.setattr(
        release_verifier,
        "import_module",
        lambda name: package if name == "cwl_context_contracts" else None,
    )
    monkeypatch.setattr(release_verifier, "files", lambda _package: resource_root)

    assert release_verifier._default_projection_sdk_verified() is False


def test_default_projection_sdk_probe_rejects_schema_version_drift(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A release cannot pass while its admitted Context Assertion schema has drifted."""

    event = {"data": {"assertion": "fixture"}}

    class Admission:
        """Minimal receipt with a deliberately incompatible schema version."""

        def __init__(self) -> None:
            self.envelope = SimpleNamespace(to_mapping=lambda: event)
            self.assertion = SimpleNamespace(to_mapping=lambda: event["data"])
            self.schema_version = 2
            self.profile_id = (
                "urn:cwl:context-contracts:context-assertion-event-semantics:v1"
            )
            self.profile_version = 1
            self.message_profile_id = (
                "urn:cwl:context-contracts:context-assertion-message-admission:v1"
            )
            self.message_profile_version = 1
            self.admission_version = 1

    package = SimpleNamespace(
        CONTEXT_ASSERTION_STRUCTURED_MEDIA_TYPE="application/cloudevents+json",
        ContextAssertionAdmission=Admission,
        admit_context_assertion_message=lambda _media_type, _event: Admission(),
    )
    profile_resource = SimpleNamespace(
        read_text=lambda **_kwargs: json.dumps(
            {"valid_vectors": [{"value": event}]}
        )
    )
    resource_root = SimpleNamespace(joinpath=lambda _name: profile_resource)

    monkeypatch.setattr(
        release_verifier,
        "import_module",
        lambda name: package if name == "cwl_context_contracts" else None,
    )
    monkeypatch.setattr(release_verifier, "files", lambda _package: resource_root)

    assert release_verifier._default_projection_sdk_verified() is False


def test_default_projection_sdk_probe_accepts_exact_projection_receipt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The exact schema and profile receipt remains admissible after hardening."""

    event = {"data": {"assertion": "fixture"}}

    class Admission:
        """Minimal exact installed-provider receipt for the positive gate path."""

        def __init__(self) -> None:
            self.envelope = SimpleNamespace(to_mapping=lambda: event)
            self.assertion = SimpleNamespace(to_mapping=lambda: event["data"])
            self.schema_version = 1
            self.profile_id = (
                "urn:cwl:context-contracts:context-assertion-event-semantics:v1"
            )
            self.profile_version = 1
            self.message_profile_id = (
                "urn:cwl:context-contracts:context-assertion-message-admission:v1"
            )
            self.message_profile_version = 1
            self.admission_version = 1

    package = SimpleNamespace(
        CONTEXT_ASSERTION_STRUCTURED_MEDIA_TYPE="application/cloudevents+json",
        ContextAssertionAdmission=Admission,
        admit_context_assertion_message=lambda _media_type, _event: Admission(),
    )
    profile_resource = SimpleNamespace(
        read_text=lambda **_kwargs: json.dumps(
            {"valid_vectors": [{"value": event}]}
        )
    )
    resource_root = SimpleNamespace(joinpath=lambda _name: profile_resource)

    monkeypatch.setattr(
        release_verifier,
        "import_module",
        lambda name: package if name == "cwl_context_contracts" else None,
    )
    monkeypatch.setattr(release_verifier, "files", lambda _package: resource_root)

    assert release_verifier._default_projection_sdk_verified() is True
