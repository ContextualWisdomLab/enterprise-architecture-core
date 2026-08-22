"""Reject lossy parsed attestation views that differ from signed DSSE bytes."""

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
_EXPECTED_SBOM = {
    "@context": "https://spdx.org/rdf/3.0.1/spdx-context.jsonld",
    "score": 9007199254740992,
}


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


def _verification_result(
    *,
    predicate_type: str,
    signed_predicate_json: str,
    parsed_predicate: object,
) -> str:
    """Build a gh-style result with independent signed and parsed statement views."""
    signed_statement = (
        '{"_type":"https://in-toto.io/Statement/v1",'
        f'"subject":[{{"digest":{{"sha256":"{_ARTIFACT_DIGEST}"}}}}],'
        f'"predicateType":"{predicate_type}",'
        f'"predicate":{signed_predicate_json}'
        "}"
    ).encode()
    encoded = base64.b64encode(signed_statement).decode("ascii")
    return json.dumps(
        [
            {
                "verificationResult": {
                    "statement": {"predicate": parsed_predicate},
                },
                "attestation": {
                    "bundle": {
                        "dsseEnvelope": {
                            "payloadType": "application/vnd.in-toto+json",
                            "payload": encoded,
                        }
                    }
                },
            }
        ]
    )


def test_verifier_uses_exact_signed_spdx_payload_not_lossy_parsed_view(
    tmp_path: Path,
) -> None:
    """Reject a signed decimal that aliases to the downloaded SBOM after rounding."""
    evidence_dir = tmp_path / "evidence"
    evidence_dir.mkdir()
    (evidence_dir / "enterprise_architecture_core-0.1-py3-none-any.whl").write_bytes(
        _ARTIFACT_BYTES
    )
    (evidence_dir / "enterprise_architecture_core-0.1.tar.gz").write_bytes(
        _ARTIFACT_BYTES
    )
    (evidence_dir / "enterprise-architecture-core.spdx.json").write_text(
        json.dumps(_EXPECTED_SBOM),
        encoding="utf-8",
    )

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    gh_path = bin_dir / "gh"
    gh_path.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        'if [[ " $* " == *" --predicate-type '
        'https://spdx.dev/Document/v3 "* ]]; then\n'
        '  printf \'%s\\n\' "$GH_FAKE_SBOM_RESULT"\n'
        "else\n"
        '  printf \'%s\\n\' "$GH_FAKE_PROVENANCE_RESULT"\n'
        "fi\n",
        encoding="utf-8",
    )
    gh_path.chmod(0o755)

    provenance = _provenance_predicate()
    env = os.environ.copy()
    env.update(
        {
            "PATH": f"{bin_dir}{os.pathsep}{env['PATH']}",
            "GH_FAKE_PROVENANCE_RESULT": _verification_result(
                predicate_type="https://slsa.dev/provenance/v1",
                signed_predicate_json=json.dumps(
                    provenance,
                    separators=(",", ":"),
                ),
                parsed_predicate=provenance,
            ),
            "GH_FAKE_SBOM_RESULT": _verification_result(
                predicate_type="https://spdx.dev/Document/v3",
                signed_predicate_json=(
                    '{"@context":"https://spdx.org/rdf/3.0.1/spdx-context.jsonld",'
                    '"score":9007199254740993.0}'
                ),
                parsed_predicate=_EXPECTED_SBOM,
            ),
            "SOURCE_SHA": _SOURCE_SHA,
            "SOURCE_REF": _SOURCE_REF,
            "EXPECTED_SOURCE_REF": _SOURCE_REF,
            "REPOSITORY": _REPOSITORY,
            "SIGNER_WORKFLOW": _SIGNER_WORKFLOW,
            "SPDX_PREDICATE": "https://spdx.dev/Document/v3",
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

    assert result.returncode != 0
    assert "exact signed payload differs" in result.stderr
