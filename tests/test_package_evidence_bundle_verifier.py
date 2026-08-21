"""Exercise downloaded package-evidence admission before protected-main signing."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

_SCRIPT_PATH = Path("scripts/verify_package_evidence_bundle.py")
_SBOM_NAME = "enterprise-architecture-core.spdx.json"
_WHEEL_NAME = "enterprise_architecture_core-0.1.0-py3-none-any.whl"
_SDIST_NAME = "enterprise_architecture_core-0.1.0.tar.gz"


def _digest(path: Path) -> str:
    """Return the SHA-256 digest of one test artifact."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_valid_bundle(
    tmp_path: Path,
    *,
    wheel_name: str = _WHEEL_NAME,
    sdist_name: str = _SDIST_NAME,
) -> Path:
    """Create one minimal internally coherent package-evidence bundle."""
    evidence_dir = tmp_path / "evidence"
    evidence_dir.mkdir()
    wheel = evidence_dir / wheel_name
    sdist = evidence_dir / sdist_name
    sbom = evidence_dir / _SBOM_NAME
    wheel.write_bytes(b"wheel")
    sdist.write_bytes(b"sdist")
    sbom.write_text(
        json.dumps(
            {
                "@context": "https://spdx.org/rdf/3.0.1/spdx-context.jsonld",
                "@graph": [
                    {"type": "CreationInfo", "specVersion": "3.0.1"},
                    {"type": "software_Package", "name": "example"},
                ],
            }
        ),
        encoding="utf-8",
    )
    checksum_lines = [
        f"{_digest(wheel)}  {wheel.name}",
        f"{_digest(sdist)}  {sdist.name}",
        f"{_digest(sbom)}  {sbom.name}",
    ]
    (evidence_dir / "SHA256SUMS").write_text(
        "\n".join(checksum_lines) + "\n",
        encoding="utf-8",
    )
    return evidence_dir


def _run_verifier(evidence_dir: Path) -> subprocess.CompletedProcess[str]:
    """Execute downloaded-evidence admission against one test directory."""
    return subprocess.run(
        ["python", str(_SCRIPT_PATH), str(evidence_dir)],
        check=False,
        capture_output=True,
        text=True,
    )


def test_package_evidence_bundle_accepts_exact_coherent_shape(tmp_path: Path) -> None:
    """Accept one wheel, one sdist, canonical SPDX 3, and exact checksums."""
    result = _run_verifier(_write_valid_bundle(tmp_path))

    assert result.returncode == 0, result.stderr


def test_package_evidence_bundle_rejects_checksum_drift(tmp_path: Path) -> None:
    """Never sign package bytes whose retained checksum no longer matches."""
    evidence_dir = _write_valid_bundle(tmp_path)
    (evidence_dir / _WHEEL_NAME).write_bytes(b"replacement")

    result = _run_verifier(evidence_dir)

    assert result.returncode != 0
    assert "checksum mismatch" in result.stderr


def test_package_evidence_bundle_rejects_extra_distribution(tmp_path: Path) -> None:
    """Never sign a mixed package bundle with an unexpected extra distribution."""
    evidence_dir = _write_valid_bundle(tmp_path)
    (evidence_dir / "enterprise_architecture_core-0.2-py3-none-any.whl").write_bytes(
        b"extra"
    )

    result = _run_verifier(evidence_dir)

    assert result.returncode != 0
    assert "exactly one wheel and one source distribution" in result.stderr


def test_package_evidence_bundle_rejects_foreign_distribution(tmp_path: Path) -> None:
    """Never sign a coherent wheel bundle for a different project identity."""
    evidence_dir = _write_valid_bundle(
        tmp_path,
        wheel_name="other_project-0.1.0-py3-none-any.whl",
    )

    result = _run_verifier(evidence_dir)

    assert result.returncode != 0
    assert "distribution identity/version" in result.stderr


def test_package_evidence_bundle_rejects_mixed_distribution_versions(
    tmp_path: Path,
) -> None:
    """Never sign wheel and sdist evidence from different project versions."""
    evidence_dir = _write_valid_bundle(
        tmp_path,
        sdist_name="enterprise_architecture_core-0.2.0.tar.gz",
    )

    result = _run_verifier(evidence_dir)

    assert result.returncode != 0
    assert "distribution identity/version" in result.stderr


def test_package_evidence_bundle_rejects_symlinked_evidence(tmp_path: Path) -> None:
    """Never follow a downloaded evidence symlink before protected-main signing."""
    evidence_dir = _write_valid_bundle(tmp_path)
    sbom_path = evidence_dir / _SBOM_NAME
    target_path = tmp_path / "outside.spdx.json"
    target_path.write_bytes(sbom_path.read_bytes())
    sbom_path.unlink()
    sbom_path.symlink_to(target_path)

    result = _run_verifier(evidence_dir)

    assert result.returncode != 0
    assert "symlink" in result.stderr
