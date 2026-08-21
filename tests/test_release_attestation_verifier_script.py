"""Exercise the protected-release attestation verifier as an executable boundary."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any

_SCRIPT_PATH = Path("scripts/verify_release_attestations.sh")
_SOURCE_SHA = "a" * 40
_REPOSITORY = "ContextualWisdomLab/enterprise-architecture-core"
_SIGNER_WORKFLOW = (
    "ContextualWisdomLab/enterprise-architecture-core/.github/workflows/supply-chain.yml"
)
_EXPECTED_SBOM: dict[str, Any] = {
    "@context": "https://spdx.org/rdf/3.0.1/spdx-context.jsonld",
    "@graph": [
        {
            "type": "software_Package",
            "name": "enterprise-architecture-core",
        }
    ],
}


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
        'if [[ -n "${GH_FAKE_REPLACEMENT_SBOM:-}" ]]; then\n'
        '  printf \'%s\\n\' "$GH_FAKE_REPLACEMENT_SBOM" > "$GH_FAKE_SBOM_PATH"\n'
        "fi\n"
        "if [[ \" $* \" == *\" --predicate-type \"* ]]; then\n"
        "  printf '%s\\n' \"$GH_FAKE_SBOM_RESULT\"\n"
        '  if [[ -n "${GH_FAKE_SYMLINK_TARGET:-}" ]]; then\n'
        '    artifact_name="${3##*/}"\n'
        '    verification_path="$GH_FAKE_VERIFICATION_DIR/$artifact_name.sbom.json"\n'
        '    rm -f "$verification_path"\n'
        '    ln -s "$GH_FAKE_SYMLINK_TARGET" "$verification_path"\n'
        "  fi\n"
        "else\n"
        "  printf '[{\"verificationResult\":{\"statement\":{\"predicate\":{}}}}]\\n'\n"
        "fi\n",
        encoding="utf-8",
    )
    gh_path.chmod(0o755)
    return bin_dir, log_path


def _run_verifier(
    tmp_path: Path,
    artifact_names: tuple[str, ...],
    *,
    source_ref: str = "refs/heads/main",
    attested_sbom: dict[str, Any] | None = None,
    include_downloaded_sbom: bool = True,
    replacement_downloaded_sbom: dict[str, Any] | None = None,
    verification_dir_kind: str | None = None,
    symlink_verification_output: bool = False,
) -> subprocess.CompletedProcess[str]:
    """Run the verifier with isolated evidence and a fake GitHub CLI."""
    evidence_dir = tmp_path / "evidence"
    evidence_dir.mkdir()
    for artifact_name in artifact_names:
        (evidence_dir / artifact_name).write_bytes(b"artifact")
    sbom_path = evidence_dir / "enterprise-architecture-core.spdx.json"
    if include_downloaded_sbom:
        sbom_path.write_text(json.dumps(_EXPECTED_SBOM), encoding="utf-8")

    bin_dir, log_path = _write_fake_gh(tmp_path)
    verification_dir = tmp_path / "verification"
    if verification_dir_kind == "directory":
        verification_dir.mkdir()
    elif verification_dir_kind == "symlink":
        existing_dir = tmp_path / "existing-verification"
        existing_dir.mkdir()
        verification_dir.symlink_to(existing_dir, target_is_directory=True)
    elif verification_dir_kind is not None:
        raise ValueError(
            f"unknown verification directory kind: {verification_dir_kind}"
        )
    signed_sbom = _EXPECTED_SBOM if attested_sbom is None else attested_sbom
    sbom_result = [
        {
            "verificationResult": {
                "statement": {"predicate": signed_sbom},
            }
        }
    ]
    env = os.environ.copy()
    env.update(
        {
            "PATH": f"{bin_dir}{os.pathsep}{env['PATH']}",
            "GH_FAKE_LOG": str(log_path),
            "GH_FAKE_SBOM_RESULT": json.dumps(sbom_result),
            "GH_FAKE_SBOM_PATH": str(sbom_path),
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
    if replacement_downloaded_sbom is not None:
        env["GH_FAKE_REPLACEMENT_SBOM"] = json.dumps(replacement_downloaded_sbom)
    if symlink_verification_output:
        symlink_target = tmp_path / "attacker-verification.json"
        symlink_target.write_text(json.dumps(sbom_result), encoding="utf-8")
        env["GH_FAKE_VERIFICATION_DIR"] = str(verification_dir)
        env["GH_FAKE_SYMLINK_TARGET"] = str(symlink_target)
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


def test_verifier_requires_downloaded_spdx_document(tmp_path: Path) -> None:
    """Fail closed when the signed predicate has no downloaded SBOM to bind."""
    result = _run_verifier(
        tmp_path,
        (
            "enterprise_architecture_core-0.1-py3-none-any.whl",
            "enterprise_architecture_core-0.1.tar.gz",
        ),
        include_downloaded_sbom=False,
    )

    assert result.returncode != 0
    assert "expected one regular downloaded SPDX evidence document" in result.stderr
    assert not (tmp_path / "gh.log").exists()


def test_verifier_rejects_existing_verification_directory(tmp_path: Path) -> None:
    """Reject a reused output directory before invoking GitHub CLI."""
    result = _run_verifier(
        tmp_path,
        (
            "enterprise_architecture_core-0.1-py3-none-any.whl",
            "enterprise_architecture_core-0.1.tar.gz",
        ),
        verification_dir_kind="directory",
    )

    assert result.returncode != 0
    assert (
        "refusing to reuse existing attestation verification directory"
        in result.stderr
    )
    assert not (tmp_path / "gh.log").exists()


def test_verifier_rejects_existing_verification_directory_symlink(
    tmp_path: Path,
) -> None:
    """Reject a symlink occupying the verification output namespace."""
    result = _run_verifier(
        tmp_path,
        (
            "enterprise_architecture_core-0.1-py3-none-any.whl",
            "enterprise_architecture_core-0.1.tar.gz",
        ),
        verification_dir_kind="symlink",
    )

    assert result.returncode != 0
    assert (
        "refusing to reuse existing attestation verification directory"
        in result.stderr
    )
    assert not (tmp_path / "gh.log").exists()


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
    assert (tmp_path / "verification").stat().st_mode & 0o777 == 0o700
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


def test_verifier_rejects_attested_spdx_predicate_drift(tmp_path: Path) -> None:
    """Reject an SPDX attestation whose signed predicate is not the downloaded SBOM."""
    attested_sbom = {
        **_EXPECTED_SBOM,
        "@graph": [
            {
                "type": "software_Package",
                "name": "different-package",
            }
        ],
    }
    result = _run_verifier(
        tmp_path,
        (
            "enterprise_architecture_core-0.1-py3-none-any.whl",
            "enterprise_architecture_core-0.1.tar.gz",
        ),
        attested_sbom=attested_sbom,
    )

    assert result.returncode != 0
    assert (
        "attested SPDX predicate does not match downloaded package SBOM"
        in result.stderr
    )


def test_verifier_rejects_mid_verification_downloaded_sbom_replacement(
    tmp_path: Path,
) -> None:
    """Bind the attestation to the SBOM snapshot present before GitHub verification."""
    replacement_sbom = {
        **_EXPECTED_SBOM,
        "@graph": [
            {
                "type": "software_Package",
                "name": "replacement-package",
            }
        ],
    }
    result = _run_verifier(
        tmp_path,
        (
            "enterprise_architecture_core-0.1-py3-none-any.whl",
            "enterprise_architecture_core-0.1.tar.gz",
        ),
        attested_sbom=replacement_sbom,
        replacement_downloaded_sbom=replacement_sbom,
    )

    assert result.returncode != 0
    assert (
        "attested SPDX predicate does not match downloaded package SBOM"
        in result.stderr
    )


def test_verifier_rejects_replaced_verification_output_symlink(tmp_path: Path) -> None:
    """Reject a verification result path replaced by a symlink during gh output."""
    result = _run_verifier(
        tmp_path,
        (
            "enterprise_architecture_core-0.1-py3-none-any.whl",
            "enterprise_architecture_core-0.1.tar.gz",
        ),
        symlink_verification_output=True,
    )

    assert result.returncode != 0
    assert "unable to parse attestation/SBOM evidence strictly" in result.stderr
