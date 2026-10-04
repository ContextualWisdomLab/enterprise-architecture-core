"""Verify release downloads never reuse persistent evidence directories."""

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_attestation_initialization_always_creates_private_directory(
    tmp_path: Path,
) -> None:
    """Two initializations must not share files or remove unrelated evidence."""
    script = ROOT / ".github/scripts/prepare-evidence.sh"
    assert script.is_file()
    unrelated = tmp_path / "evidence"
    unrelated.mkdir()
    sentinel = unrelated / "preserve"
    sentinel.write_text("existing")
    paths = []
    for attempt in range(2):
        output = tmp_path / f"env-{attempt}"
        result = subprocess.run(
            ["bash", str(script)], capture_output=True, text=True, timeout=10,
            env={**os.environ, "RUNNER_TEMP": str(tmp_path),
                 "GITHUB_ENV": str(output)},
        )
        assert result.returncode == 0, result.stderr
        name, value = output.read_text().strip().split("=", 1)
        assert name == "CI_EVIDENCE"
        path = Path(value)
        assert path.parent == tmp_path
        assert not list(path.iterdir())
        paths.append(path)
    assert paths[0] != paths[1]
    assert sentinel.read_text() == "existing"
