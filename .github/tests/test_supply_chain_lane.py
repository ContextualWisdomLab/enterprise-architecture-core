"""Verify the existing SBOM gate has an executable fail-closed entrypoint."""

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_missing_sbom_fails_before_evidence_publication(tmp_path: Path) -> None:
    """Do not permit a package-only directory to become SBOM evidence."""
    script = ROOT / ".github/scripts/validate-sbom.sh"
    assert script.is_file(), "SBOM validation must live in .github"
    result = subprocess.run(
        ["bash", str(script), str(tmp_path)],
        text=True, capture_output=True, timeout=10,
    )
    assert result.returncode != 0
    assert not (tmp_path / "SHA256SUMS").exists()
