"""Exercise fail-closed release-package reproducibility admission."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_SCRIPT = Path("scripts/verify_reproducible_package_builds.py")
_WHEEL = "enterprise_architecture_core-0.1.0-py3-none-any.whl"
_SDIST = "enterprise_architecture_core-0.1.0.tar.gz"


def _write_release_pair(directory: Path, *, wheel: bytes, sdist: bytes) -> None:
    """Write one realistic wheel/sdist pair into a build directory."""
    directory.mkdir()
    (directory / _WHEEL).write_bytes(wheel)
    (directory / _SDIST).write_bytes(sdist)


def _run_verifier(first: Path, second: Path) -> subprocess.CompletedProcess[str]:
    """Run the repository verifier exactly as the supply-chain job will."""
    return subprocess.run(
        [sys.executable, str(_SCRIPT), str(first), str(second)],
        check=False,
        capture_output=True,
        text=True,
    )


def test_equal_release_builds_are_admitted(tmp_path: Path) -> None:
    """Accept byte-identical wheel and sdist outputs from two clean builds."""
    first = tmp_path / "first"
    second = tmp_path / "second"
    _write_release_pair(first, wheel=b"wheel-bytes", sdist=b"sdist-bytes")
    _write_release_pair(second, wheel=b"wheel-bytes", sdist=b"sdist-bytes")

    result = _run_verifier(first, second)

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "release package builds are byte-reproducible"


def test_changed_release_bytes_fail_closed(tmp_path: Path) -> None:
    """Reject a coherent second build whose wheel bytes differ."""
    first = tmp_path / "first"
    second = tmp_path / "second"
    _write_release_pair(first, wheel=b"wheel-a", sdist=b"sdist")
    _write_release_pair(second, wheel=b"wheel-b", sdist=b"sdist")

    result = _run_verifier(first, second)

    assert result.returncode == 1
    assert "artifact bytes differ" in result.stderr


def test_release_filename_drift_fails_closed(tmp_path: Path) -> None:
    """Reject builds that do not produce the same exact artifact names."""
    first = tmp_path / "first"
    second = tmp_path / "second"
    _write_release_pair(first, wheel=b"wheel", sdist=b"sdist")
    second.mkdir()
    (second / "enterprise_architecture_core-0.1.1-py3-none-any.whl").write_bytes(
        b"wheel"
    )
    (second / "enterprise_architecture_core-0.1.1.tar.gz").write_bytes(b"sdist")

    result = _run_verifier(first, second)

    assert result.returncode == 1
    assert "artifact names differ" in result.stderr


def test_symlinked_release_artifact_fails_closed(tmp_path: Path) -> None:
    """Reject path substitution instead of following a release-artifact symlink."""
    first = tmp_path / "first"
    second = tmp_path / "second"
    _write_release_pair(first, wheel=b"wheel", sdist=b"sdist")
    _write_release_pair(second, wheel=b"wheel", sdist=b"sdist")
    target = second / _WHEEL
    target.unlink()
    target.symlink_to(first / _WHEEL)

    result = _run_verifier(first, second)

    assert result.returncode == 1
    assert "regular file" in result.stderr
