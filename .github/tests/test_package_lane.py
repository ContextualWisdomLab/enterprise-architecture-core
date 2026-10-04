"""Verify package lane builds only fresh, installable distributions."""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def test_package_lane_ignores_stale_workspace_distribution(tmp_path: Path) -> None:
    """Build and install from a new directory, not persistent workspace dist."""
    script = ROOT / ".github/scripts/package.sh"
    assert script.is_file(), "package lane must be runnable outside YAML"
    output = tmp_path / "github-env"
    output.touch()
    work = None
    try:
        result = subprocess.run(
            ["bash", str(script)], cwd=ROOT, text=True, capture_output=True,
            env={
                **os.environ,
                "GITHUB_ENV": str(output),
                "PYTHON_VERSION": "3.14",
                "RUNNER_TEMP": str(tmp_path),
            },
            timeout=120,
        )
        line, = output.read_text().splitlines()
        name, path = line.split("=", 1)
        assert name == "CI_DIST"
        dist = Path(path)
        assert dist.parent.parent.resolve() == tmp_path.resolve()
        assert dist.parent.name.startswith("ea-package.")
        work = dist.parent
        assert result.returncode == 0, result.stdout + result.stderr
        assert dist.resolve() != (ROOT / "dist").resolve()
        assert len(list(dist.glob("*.whl"))) == 1
        assert len(list(dist.glob("*.tar.gz"))) == 1
        assert "installed package smoke: OK" in result.stdout
    finally:
        if work is not None:
            shutil.rmtree(work)


@pytest.mark.parametrize("fail_assertion", [False, True])
def test_package_test_cleans_only_its_owned_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fail_assertion: bool,
) -> None:
    """Check test-owned artifact cleanup on success and assertion failure."""
    lane = tmp_path / "lane"
    lane.mkdir()
    unrelated = lane / "ea-package.preexisting"
    unrelated.mkdir()
    marker = unrelated / "keep"
    marker.write_text("unrelated artifacts")
    monkeypatch.setenv("RUNNER_TEMP", str(lane))
    monkeypatch.setenv("TMPDIR", str(lane))
    if fail_assertion:
        real_run = subprocess.run

        def run_without_smoke_message(*args, **kwargs):
            result = real_run(*args, **kwargs)
            result.stdout = result.stdout.replace("installed package smoke: OK", "")
            return result

        monkeypatch.setattr(subprocess, "run", run_without_smoke_message)
    try:
        if fail_assertion:
            with pytest.raises(AssertionError, match="installed package smoke"):
                test_package_lane_ignores_stale_workspace_distribution(lane)
        else:
            test_package_lane_ignores_stale_workspace_distribution(lane)
        assert marker.read_text() == "unrelated artifacts"
        assert set(lane.iterdir()) == {unrelated, lane / "github-env"}, (
            "package test leaked its retained distribution directory"
        )
    finally:
        # Clean the exact receipt-owned path even when reproducing a RED leak.
        output = lane / "github-env"
        if output.exists():
            for line in output.read_text().splitlines():
                if line.startswith("CI_DIST="):
                    work = Path(line.split("=", 1)[1]).parent
                    assert work.parent.resolve() == lane.resolve()
                    assert work.name.startswith("ea-package.")
                    assert work != unrelated
                    if work.exists():
                        shutil.rmtree(work)
