"""Exercise strict GitHub Actions SLSA provenance admission policy."""

from __future__ import annotations

import base64
import copy
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

_SCRIPT_PATH = Path("scripts/verify_attestation_output.py")
_SOURCE_SHA = "a" * 40
_ARTIFACT_DIGEST = hashlib.sha256(b"artifact").hexdigest()
_REPOSITORY = "ContextualWisdomLab/enterprise-architecture-core"
_SOURCE_REF = "refs/heads/main"
_WORKFLOW_PATH = ".github/workflows/supply-chain.yml"
_SIGNER_WORKFLOW = f"{_REPOSITORY}/{_WORKFLOW_PATH}"
_BUILD_TYPE = "https://actions.github.io/buildtypes/workflow/v1"
_PREDICATE_TYPE = "https://slsa.dev/provenance/v1"
_POLICY_ERROR = "provenance predicate does not match expected GitHub Actions build"


def _provenance_predicate() -> dict[str, Any]:
    """Return the exact policy-relevant shape emitted by pinned actions/attest."""
    return {
        "buildDefinition": {
            "buildType": _BUILD_TYPE,
            "externalParameters": {
                "workflow": {
                    "ref": _SOURCE_REF,
                    "repository": f"https://github.com/{_REPOSITORY}",
                    "path": _WORKFLOW_PATH,
                }
            },
            "internalParameters": {
                "github": {
                    "event_name": "push",
                    "repository_id": "123",
                    "repository_owner_id": "456",
                    "runner_environment": "github-hosted",
                }
            },
            "resolvedDependencies": [
                {
                    "uri": f"git+https://github.com/{_REPOSITORY}@{_SOURCE_REF}",
                    "digest": {"gitCommit": _SOURCE_SHA},
                }
            ],
        },
        "runDetails": {
            "builder": {
                "id": f"https://github.com/{_SIGNER_WORKFLOW}@{_SOURCE_REF}"
            },
            "metadata": {
                "invocationId": (
                    f"https://github.com/{_REPOSITORY}/actions/runs/123/attempts/1"
                )
            },
        },
    }


def _verification_result(predicate: dict[str, Any]) -> list[dict[str, Any]]:
    """Wrap a predicate in the signed DSSE shape returned by gh attestation verify."""
    statement = {
        "_type": "https://in-toto.io/Statement/v1",
        "subject": [{"digest": {"sha256": _ARTIFACT_DIGEST}}],
        "predicateType": _PREDICATE_TYPE,
        "predicate": predicate,
    }
    payload = json.dumps(statement, sort_keys=True, separators=(",", ":")).encode()
    return [
        {
            "attestation": {
                "bundle": {
                    "dsseEnvelope": {
                        "payloadType": "application/vnd.in-toto+json",
                        "payload": base64.b64encode(payload).decode("ascii"),
                    }
                }
            },
            "verificationResult": {"statement": statement},
        }
    ]


def _run_verifier(
    tmp_path: Path, predicate: dict[str, Any]
) -> subprocess.CompletedProcess[str]:
    """Run the verifier with the release workflow identity supplied by its caller."""
    env = os.environ.copy()
    env.update(
        {
            "SOURCE_SHA": _SOURCE_SHA,
            "EXPECTED_SOURCE_REF": _SOURCE_REF,
            "REPOSITORY": _REPOSITORY,
            "SIGNER_WORKFLOW": _SIGNER_WORKFLOW,
        }
    )
    return subprocess.run(
        [
            sys.executable,
            str(_SCRIPT_PATH),
            str(tmp_path / "verified.json"),
            _ARTIFACT_DIGEST,
            _PREDICATE_TYPE,
        ],
        input=json.dumps(_verification_result(predicate)),
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )


def test_provenance_accepts_exact_pinned_actions_attest_identity(
    tmp_path: Path,
) -> None:
    """Accept the exact source/workflow identity produced by the pinned action."""
    result = _run_verifier(tmp_path, _provenance_predicate())

    assert result.returncode == 0, result.stderr
    assert (tmp_path / "verified.json").is_file()


def test_provenance_rejects_missing_slsa_build_definition(tmp_path: Path) -> None:
    """Do not retain a typed but content-free provenance predicate."""
    result = _run_verifier(tmp_path, {})

    assert result.returncode != 0
    assert _POLICY_ERROR in result.stderr
    assert not (tmp_path / "verified.json").exists()


def test_provenance_rejects_wrong_workflow_ref(tmp_path: Path) -> None:
    """Bind external workflow parameters to the protected release ref."""
    predicate = _provenance_predicate()
    predicate["buildDefinition"]["externalParameters"]["workflow"]["ref"] = (
        "refs/heads/develop"
    )

    result = _run_verifier(tmp_path, predicate)

    assert result.returncode != 0
    assert _POLICY_ERROR in result.stderr


def test_provenance_rejects_wrong_resolved_source_digest(tmp_path: Path) -> None:
    """Require the signed source dependency to name the exact release commit."""
    predicate = _provenance_predicate()
    predicate["buildDefinition"]["resolvedDependencies"][0]["digest"][
        "gitCommit"
    ] = "b" * 40

    result = _run_verifier(tmp_path, predicate)

    assert result.returncode != 0
    assert _POLICY_ERROR in result.stderr


def test_provenance_rejects_wrong_builder_identity(tmp_path: Path) -> None:
    """Require SLSA run details to identify the expected pinned workflow path/ref."""
    predicate = _provenance_predicate()
    predicate["runDetails"]["builder"]["id"] = (
        f"https://github.com/{_REPOSITORY}/.github/workflows/other.yml@{_SOURCE_REF}"
    )

    result = _run_verifier(tmp_path, predicate)

    assert result.returncode != 0
    assert _POLICY_ERROR in result.stderr


def test_provenance_rejects_unexpected_external_parameter(tmp_path: Path) -> None:
    """Reject undeclared caller-controlled inputs at the SLSA trust boundary."""
    predicate = copy.deepcopy(_provenance_predicate())
    predicate["buildDefinition"]["externalParameters"]["extra"] = "surprise"

    result = _run_verifier(tmp_path, predicate)

    assert result.returncode != 0
    assert _POLICY_ERROR in result.stderr
