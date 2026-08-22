"""Require explicit predicate selection for every release attestation lookup."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import subprocess
from pathlib import Path

_SCRIPT_PATH = Path("scripts/verify_release_attestations.sh")
_SOURCE_SHA = "a" * 40
_REPOSITORY = "ContextualWisdomLab/enterprise-architecture-core"
_SOURCE_REF = "refs/heads/main"
_WORKFLOW_PATH = ".github/workflows/supply-chain.yml"
_SIGNER_WORKFLOW = f"{_REPOSITORY}/{_WORKFLOW_PATH}"
_ARTIFACT_BYTES = b"artifact"
_ARTIFACT_DIGEST = hashlib.sha256(_ARTIFACT_BYTES).hexdigest()
_PROVENANCE_PREDICATE = "https://slsa.dev/provenance/v1"
_SPDX_PREDICATE = "https://spdx.dev/Document/v3"
_SBOM = {"name": "enterprise-architecture-core"}


def _provenance_predicate() -> dict[str, object]:
    """Return the policy-relevant SLSA predicate emitted by pinned actions/attest."""
    return {
        "buildDefinition": {
            "buildType": "https://actions.github.io/buildtypes/workflow/v1",
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


def _signed_result(predicate_type: str, predicate: object) -> str:
    """Build one verified GitHub-style result with an exact signed statement."""
    statement = {
        "_type": "https://in-toto.io/Statement/v1",
        "subject": [{"digest": {"sha256": _ARTIFACT_DIGEST}}],
        "predicateType": predicate_type,
        "predicate": predicate,
    }
    payload = base64.b64encode(
        json.dumps(statement, separators=(",", ":")).encode("utf-8")
    ).decode("ascii")
    return json.dumps(
        [
            {
                "verificationResult": {"statement": statement},
                "attestation": {
                    "bundle": {
                        "dsseEnvelope": {
                            "payloadType": "application/vnd.in-toto+json",
                            "payload": payload,
                        }
                    }
                },
            }
        ]
    )


def test_every_attestation_lookup_selects_its_predicate_explicitly(
    tmp_path: Path,
) -> None:
    """Do not rely on the GitHub CLI default predicate when multiple types exist."""
    evidence_dir = tmp_path / "evidence"
    evidence_dir.mkdir()
    (evidence_dir / "enterprise_architecture_core-0.1-py3-none-any.whl").write_bytes(
        _ARTIFACT_BYTES
    )
    (evidence_dir / "enterprise_architecture_core-0.1.tar.gz").write_bytes(
        _ARTIFACT_BYTES
    )
    (evidence_dir / "enterprise-architecture-core.spdx.json").write_text(
        json.dumps(_SBOM),
        encoding="utf-8",
    )

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    gh_path = bin_dir / "gh"
    gh_path.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        'case " $* " in\n'
        f'  *" --predicate-type {_PROVENANCE_PREDICATE} "*) '
        'printf \'%s\\n\' "$GH_PROVENANCE" ;;\n'
        f'  *" --predicate-type {_SPDX_PREDICATE} "*) '
        'printf \'%s\\n\' "$GH_SBOM" ;;\n'
        '  *) echo "missing explicit predicate type" >&2; exit 9 ;;\n'
        "esac\n",
        encoding="utf-8",
    )
    gh_path.chmod(0o755)

    env = os.environ.copy()
    env.update(
        {
            "PATH": f"{bin_dir}{os.pathsep}{env['PATH']}",
            "GH_PROVENANCE": _signed_result(
                _PROVENANCE_PREDICATE,
                _provenance_predicate(),
            ),
            "GH_SBOM": _signed_result(_SPDX_PREDICATE, _SBOM),
            "SOURCE_SHA": _SOURCE_SHA,
            "SOURCE_REF": _SOURCE_REF,
            "EXPECTED_SOURCE_REF": _SOURCE_REF,
            "REPOSITORY": _REPOSITORY,
            "SIGNER_WORKFLOW": _SIGNER_WORKFLOW,
            "SPDX_PREDICATE": _SPDX_PREDICATE,
            "EVIDENCE_DIR": str(evidence_dir),
            "VERIFICATION_DIR": str(tmp_path / "verification"),
        }
    )

    result = subprocess.run(
        ["bash", str(_SCRIPT_PATH)],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode == 0, result.stderr
