"""Guard the repository CI's dedicated self-hosted admission boundary."""

import os
import re
import subprocess
from pathlib import Path

import pytest

WORKFLOWS = tuple(sorted(Path(".github/workflows").glob("*.yml")))
CANDIDATE_JOBS = (
    ("ci", "validate"),
    ("ci", "postgres-migration"),
    ("ci", "compose-runtime"),
    ("ci", "package"),
    ("runtime-readiness", "installed-process-readiness"),
    ("supply-chain", "package-evidence"),
)
ADMISSION_STEP = (
    "      - name: Admit trusted source\n"
    "        env:\n"
    "          SOURCE_REPOSITORY: "
    "${{ github.event.pull_request.head.repo.full_name || github.repository }}\n"
    "          EXPECTED_REPOSITORY: ${{ github.repository }}\n"
    '        run: test "$SOURCE_REPOSITORY" = "$EXPECTED_REPOSITORY"\n'
)


def test_every_executable_job_requires_dedicated_self_hosted_linux() -> None:
    """Reject hosted fallback and accidental use of general-purpose hosts."""
    assert len(WORKFLOWS) == 3
    jobs = 0
    candidates = []
    for path in WORKFLOWS:
        text = path.read_text().split("jobs:\n", 1)[1]
        for name, body in re.findall(
            r"^  ([a-z-]+):\n(.*?)(?=^  [a-z-]+:|\Z)", text, re.M | re.S
        ):
            selector, = re.findall(r"^    runs-on: (.+)$", body, re.M)
            jobs += 1
            assert selector in {
                "[self-hosted, linux, x64, ea-core-ci]",
                "[self-hosted, linux, x64, ea-core-release-ci]",
            }, path
            if selector.endswith("ea-core-ci]"):
                candidates.append((path.stem, name))
    assert jobs == 7
    assert sorted(candidates) == sorted(CANDIDATE_JOBS)


@pytest.mark.parametrize(("workflow", "job"), CANDIDATE_JOBS)
def test_candidate_fails_closed_before_any_checkout_or_action(
    workflow: str, job: str,
) -> None:
    """Keep existing checks failing on forks instead of skipped-success jobs."""
    text = Path(f".github/workflows/{workflow}.yml").read_text()
    body, = re.findall(
        rf"^  {job}:\n(.*?)(?=^  [a-z-]+:|\Z)", text, re.M | re.S
    )
    config, steps = body.split("    steps:\n", 1)
    assert "    if:" not in config, "fork checks must run and explicitly fail"
    assert steps.startswith(ADMISSION_STEP), "admission must precede all execution"
    assert steps[len(ADMISSION_STEP):].startswith("      - uses: actions/checkout@")
    assert "continue-on-error:" not in body
    assert "        if:" not in steps, "later steps must retain default success gating"


@pytest.mark.parametrize(("workflow", "job"), CANDIDATE_JOBS)
@pytest.mark.parametrize(
    ("source_repository", "expected_status"),
    [("owner/repository", 0), ("fork/repository", 1)],
)
def test_real_admission_shell_accepts_same_repository_and_rejects_fork(
    workflow: str, job: str, source_repository: str, expected_status: int,
    tmp_path: Path,
) -> None:
    """Execute each job's inline admission without a checkout or local scripts."""
    text = Path(f".github/workflows/{workflow}.yml").read_text()
    body, = re.findall(
        rf"^  {job}:\n(.*?)(?=^  [a-z-]+:|\Z)", text, re.M | re.S
    )
    first = body.split("    steps:\n", 1)[1].split("\n      - ", 1)[0]
    assert "- name: Admit trusted source" in first
    command, = re.findall(r"^        run: (.+)$", first, re.M)
    result = subprocess.run(
        ["bash", "--noprofile", "--norc", "-eo", "pipefail", "-c", command],
        env={
            **os.environ,
            "SOURCE_REPOSITORY": source_repository,
            "EXPECTED_REPOSITORY": "owner/repository",
        },
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == expected_status, result.stdout + result.stderr
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize(
    "path",
    [
        ".github/compose.ci.yaml",
        "compose.yaml",
        ".github/workflows/ci.yml",
    ],
)
def test_database_health_waits_for_final_tcp_server(path: str) -> None:
    """Healthy must mean the post-init TCP server, not the init socket server.

    The PostgreSQL image runs init scripts on a socket-only temporary server.
    A socket ``pg_isready`` reports healthy then, and the following restart
    closes the first host TCP connection.
    """
    text = Path(path).read_text()
    probes = re.findall(r"pg_isready[^\"\]\n]*", text)
    assert probes, path
    assert all("-h 127.0.0.1" in probe for probe in probes), probes


def test_supply_chain_pr_cannot_reach_release_pool() -> None:
    """Isolate write/OIDC authority from candidate pull-request jobs."""
    workflow = Path(".github/workflows/supply-chain.yml").read_text()
    producer, release = workflow.split("  attest-protected-main:")
    assert ADMISSION_STEP in producer
    assert "ea-core-release-ci" not in producer
    assert "runs-on: [self-hosted, linux, x64, ea-core-release-ci]" in release
    assert (
        "if: github.event_name == 'push' && github.ref == 'refs/heads/main' "
        "&& github.ref_protected"
    ) in release
    assert "Admit trusted source" not in release
