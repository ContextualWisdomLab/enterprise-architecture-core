"""Exercise the protected-release attestation verifier as an executable boundary."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

_SCRIPT_PATH = Path("scripts/verify_release_attestations.sh")
_SOURCE_SHA = "a" * 40
_REPOSITORY = "ContextualWisdomLab/enterprise-architecture-core"
_SIGNER_WORKFLOW = (
    "ContextualWisdomLab/enterprise-architecture-core/.github/workflows/supply-chain.yml"
)


def _write_fake_gh(tmp_path: Path) -> tuple[Path, Path]:
    """Create a deterministic gh shim that records every invocation."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log_path = tmp_path / "gh.log"
    gh_path = bin_dir / "gh"
    gh_path.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        'printf \'%s\\n\' \"$*\" >> \"$GH_FAKE_LOG\"\n'
        "printf '{}\\n'\n",
        encoding="utf-8",
    )
    gh_path.chmod(0o755)
    return bin_dir, log_path


def _run_verifier(
    tmp_path: Path,
    artifact_names: tuple[str, ...],
    *,
    source_ref: str = "refs/heads/main",
) -> subprocess.CompletedProcess[str]:
    """Run the verifier with isolated evidence and a fake GitHub CLI."""
    evidence_dir = tmp_path / "evidence"
    evidence_dir.mkdir()
    for artifact_name in artifact_names:
        (evidence_dir / artifact_name).write_bytes(b"artifact")

    bin_dir, log_path = _write_fake_gh(tmp_path)
    verification_dir = tmp_path / "verification"
    env = os.environ.copy()
    env.update(
        {
            "PATH": f"{bin_dir}{os.pathsep}{env['PATH']}",
            "GH_FAKE_LOG": str(log_path),
            "SOURCE_SHA": _SOURCE_SHA,
            "SOURCE_REF": source_ref,
            "EXPECTED_SOURCE_REF": "refs/heads/main",
            "REPOSITORY": _REPOSITORY,
            "SIGNER_WORKFLOW": _SIGNER_WORKFLOW,
            "SPDX_PREDICATE": "https://spdx.dev/Document/v3",
            "EVIDENCE_DIR": str(evidence_dir),
            "VERIFICATION_DIR": str(verification_dir),
        }
    )
    return subprocess.run(
        ["bash", str(_SCRIPT_PATH)],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )


def test_verifier_requires_one_wheel_and_one_sdist(tmp_path: Path) -> None:
    """Reject a same-count artifact set with the wrong package shape."""
    result = _run_verifier(
        tmp_path,
        (
            "enterprise_architecture_core-0.1-py3-none-any.whl",
            "enterprise_architecture_core-0.1-py3-none-linux.whl",
        ),
    )

    assert result.returncode != 0
    assert "expected exactly one wheel and one source distribution" in result.stderr


def test_verifier_executes_both_attestation_policies(tmp_path: Path) -> None:
    """Verify exact producer identity and both predicates for both release artifacts."""
    result = _run_verifier(
        tmp_path,
        (
            "enterprise_architecture_core-0.1-py3-none-any.whl",
            "enterprise_architecture_core-0.1.tar.gz",
        ),
    )

    assert result.returncode == 0, result.stderr
    log_lines = (tmp_path / "gh.log").read_text(encoding="utf-8").splitlines()
    assert len(log_lines) == 4
    assert (
        sum(
            "--predicate-type https://spdx.dev/Document/v3" in line
            for line in log_lines
        )
        == 2
    )
    assert all(f"--repo {_REPOSITORY}" in line for line in log_lines)
    assert all(f"--source-digest {_SOURCE_SHA}" in line for line in log_lines)
    assert all("--source-ref refs/heads/main" in line for line in log_lines)
    assert all(f"--signer-digest {_SOURCE_SHA}" in line for line in log_lines)
    assert all(f"--signer-workflow {_SIGNER_WORKFLOW}" in line for line in log_lines)
    assert all(
        "--cert-oidc-issuer https://token.actions.githubusercontent.com" in line
        for line in log_lines
    )
    assert all("--deny-self-hosted-runners" in line for line in log_lines)

    verification_files = sorted(
        path.name for path in (tmp_path / "verification").glob("*.json")
    )
    assert verification_files == [
        "enterprise_architecture_core-0.1-py3-none-any.whl.provenance.json",
        "enterprise_architecture_core-0.1-py3-none-any.whl.sbom.json",
        "enterprise_architecture_core-0.1.tar.gz.provenance.json",
        "enterprise_architecture_core-0.1.tar.gz.sbom.json",
    ]


def test_verifier_rejects_non_release_ref_before_calling_gh(tmp_path: Path) -> None:
    """Fail closed before any attestation lookup outside protected main."""
    result = _run_verifier(
        tmp_path,
        (
            "enterprise_architecture_core-0.1-py3-none-any.whl",
            "enterprise_architecture_core-0.1.tar.gz",
        ),
        source_ref="refs/heads/develop",
    )

    assert result.returncode != 0
    assert "refusing attestation verification outside protected main" in result.stderr
    assert not (tmp_path / "gh.log").exists()
