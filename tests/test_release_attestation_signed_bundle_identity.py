"""Reject lossy parsed attestation views that differ from signed DSSE bytes."""

from __future__ import annotations

import base64
import json
import os
import subprocess
from pathlib import Path

_SCRIPT_PATH = Path("scripts/verify_release_attestations.sh")
_SOURCE_SHA = "a" * 40
_EXPECTED_SBOM = {
    "@context": "https://spdx.org/rdf/3.0.1/spdx-context.jsonld",
    "score": 9007199254740992,
}


def _verification_result(*, signed_predicate_json: str) -> str:
    """Build one gh-style result whose parsed view aliases a distinct signed number."""
    signed_statement = (
        '{"_type":"https://in-toto.io/Statement/v1",'
        '"subject":[],"predicateType":"https://spdx.dev/Document/v3",'
        f'"predicate":{signed_predicate_json}'
        "}"
    ).encode()
    encoded = base64.b64encode(signed_statement).decode("ascii")
    return json.dumps(
        [
            {
                "verificationResult": {
                    "statement": {"predicate": _EXPECTED_SBOM},
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
        b"wheel"
    )
    (evidence_dir / "enterprise_architecture_core-0.1.tar.gz").write_bytes(b"sdist")
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
        'if [[ " $* " == *" --predicate-type "* ]]; then\n'
        '  printf \'%s\\n\' "$GH_FAKE_SBOM_RESULT"\n'
        "else\n"
        "  printf '[{\"verificationResult\":{\"statement\":{\"predicate\":{}}}}]\\n'\n"
        "fi\n",
        encoding="utf-8",
    )
    gh_path.chmod(0o755)

    env = os.environ.copy()
    env.update(
        {
            "PATH": f"{bin_dir}{os.pathsep}{env['PATH']}",
            "GH_FAKE_SBOM_RESULT": _verification_result(
                signed_predicate_json=(
                    '{"@context":"https://spdx.org/rdf/3.0.1/spdx-context.jsonld",'
                    '"score":9007199254740993.0}'
                )
            ),
            "SOURCE_SHA": _SOURCE_SHA,
            "SOURCE_REF": "refs/heads/main",
            "EXPECTED_SOURCE_REF": "refs/heads/main",
            "REPOSITORY": "ContextualWisdomLab/enterprise-architecture-core",
            "SIGNER_WORKFLOW": (
                "ContextualWisdomLab/enterprise-architecture-core/"
                ".github/workflows/supply-chain.yml"
            ),
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
    assert "signed" in result.stderr.lower()
