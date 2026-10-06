"""Exercise repository-owned CI execution without shared runner resources."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / ".github/scripts"


def test_dispatcher_rejects_unknown_lane_without_running_tools() -> None:
    """Reject invalid lanes before creating resources or invoking dependencies."""
    result = subprocess.run(
        ["bash", str(SCRIPTS / "ci.sh"), "not-a-lane"],
        capture_output=True,
        text=True,
        check=False,
        cwd=ROOT.parent,
    )
    assert result.returncode == 2
    assert "unknown CI lane" in result.stderr


def test_validate_uses_private_environment_and_preserves_acceptance(
    tmp_path: Path,
) -> None:
    """Exercise the complete validation command sequence in isolated directories."""
    executable = tmp_path / "uv"
    log = tmp_path / "commands"
    executable.write_text(
        "#!/usr/bin/env python3\n"
        "import json, os, sys\n"
        "with open(os.environ['COMMAND_LOG'], 'a') as output:\n"
        "    output.write(json.dumps({'args': sys.argv[1:], "
        "'env': os.environ.get('UV_PROJECT_ENVIRONMENT'), "
        "'coverage': os.environ.get('COVERAGE_FILE')}) + '\\n')\n"
        "if sys.argv[1:] == ['--version']:\n"
        "    print('uv 0.11.32')\n",
        encoding="utf-8",
    )
    executable.chmod(0o755)
    environment = dict(os.environ, PATH=f"{tmp_path}:{os.environ['PATH']}")
    environment.update(COMMAND_LOG=str(log))
    result = subprocess.run(
        ["bash", str(SCRIPTS / "ci.sh"), "validate", "3.11"],
        capture_output=True,
        text=True,
        check=False,
        env=environment,
        cwd=ROOT.parent,
    )
    assert result.returncode == 0, result.stderr
    commands = [json.loads(line) for line in log.read_text().splitlines()]
    arguments = [entry["args"] for entry in commands]
    assert ["lock", "--check"] in arguments
    assert ["sync", "--locked", "--extra", "dev", "--python", "3.11"] in arguments
    joined = [" ".join(command) for command in arguments]
    for gate in (
        "python -m compileall -q src scripts .github/scripts",
        "python -m ruff check . --output-format=github",
        "python -m ruff check .github/tests --output-format=github",
        "python -m coverage run -m pytest -q tests .github/tests",
        "python -m coverage report",
        "python scripts/validate_repository.py",
    ):
        assert any(gate in command for command in joined), gate
    private = Path(commands[1]["env"])
    assert private != ROOT / ".venv"
    assert not private.parent.exists(), "lane failed to remove its temporary directory"
    assert commands[1]["coverage"].startswith(str(private.parent))


def test_sql_lane_preserves_every_original_acceptance_gate() -> None:
    """Keep migration boundary, drift, atomicity, ledger and invariant checks."""
    script = SCRIPTS / "postgres-migration.sh"
    assert script.exists(), "SQL acceptance must be an executable local lane"
    text = script.read_text()
    for gate in (
        "checksum drift was unexpectedly accepted",
        "upgrade rehearsal requires at least two migrations",
        'test "$prior_ledger_count" -eq "$latest_index"',
        'test "$upgraded_ledger_count" -eq "${#migration_paths[@]}"',
        "object_revision_evidence_required",
        "architecture_relation_evidence_required",
        "outbox_event_publish_chronology",
        "projection_receipt_process_chronology",
        "project_scenario_relations(uuid)",
        "project_transformation_state(uuid,timestamp with time zone,",
        "project_technology_change_impact(uuid,timestamp with time zone,",
        "failing migration unexpectedly committed",
        'test "$schema_absent" = "t"',
        'test "$table_count" -eq 36',
        'test "$reference_view_count" -eq 1',
        'test "$ledger_count" -eq 15',
        "database/tests/*.sql",
    ):
        assert gate in text, gate
    assert "BASH_VERSINFO" in text
    assert "ci_init postgres-migration" in text
    assert 'PGDATABASE="ea_core_ci_${database_suffix}"' in text
    assert 'probe_database="ea_core_upgrade_${database_suffix}"' in text
    assert 'probe_database="ea_core_atomicity_${database_suffix}"' in text
    assert "applied migration checksum mismatch" in text
    assert "export LC_ALL=C" in text, "SQL dependency order must ignore host locale"
    assert 'sed \'$d\' database/migrations/0001_identity_objects.sql' in text


def test_compose_lane_isolates_project_port_and_cleanup(tmp_path: Path) -> None:
    """Use random loopback publishing and clean only each acquired project."""
    executable = tmp_path / "docker"
    log = tmp_path / "commands"
    executable.write_text(
        "#!/usr/bin/env python3\n"
        "import json, os, sys\n"
        "with open(os.environ['COMMAND_LOG'], 'a') as output:\n"
        "    output.write(json.dumps(sys.argv[1:]) + '\\n')\n"
        "if 'port' in sys.argv:\n"
        "    print('127.0.0.1:49152')\n",
        encoding="utf-8",
    )
    executable.chmod(0o755)
    psql = tmp_path / "psql"
    psql.write_text(
        "#!/bin/sh\n"
        "printf '%s\\n' \"$PGPORT $*\" >> \"$PSQL_LOG\"\n",
        encoding="utf-8",
    )
    psql.chmod(0o755)
    psql_log = tmp_path / "psql-commands"
    environment = dict(os.environ, PATH=f"{tmp_path}:{os.environ['PATH']}")
    environment.update(
        COMMAND_LOG=str(log),
        PSQL_LOG=str(psql_log),
        EA_OWNER_PASSWORD="test-owner",
        EA_RUNTIME_PASSWORD="test-runtime",
    )
    projects = []
    for _ in range(2):
        result = subprocess.run(
            ["bash", str(SCRIPTS / "ci.sh"), "compose-runtime"],
            capture_output=True,
            text=True,
            check=False,
            env=environment,
            cwd=ROOT.parent,
        )
        assert result.returncode == 0, result.stderr
        calls = [json.loads(line) for line in log.read_text().splitlines()]
        scoped = [call for call in calls if "--project-name" in call]
        project = scoped[-1][scoped[-1].index("--project-name") + 1]
        projects.append(project)
        assert scoped[-1][-3:] == ["down", "--volumes", "--remove-orphans"]
        assert any(call[-3:] == ["up", "--detach", "--wait"] for call in scoped)
        assert any("port" in call for call in scoped)
    assert len(set(projects)) == 2
    assert "49152" in psql_log.read_text()
    assert "verify_runtime_role.sql" in psql_log.read_text()
    text = (ROOT / ".github/compose.ci.yaml").read_text()
    assert '"127.0.0.1::5432"' in text
    assert "../database/migrations" in text
    assert "54328" not in text


def test_installed_process_probe_uses_dynamic_ports_and_cleans_up(
    tmp_path: Path,
) -> None:
    """Run the real entry point twice without fixed HTTP ports or surviving children."""
    import sys

    executable = Path(sys.executable).parent / "ea-core"
    assert executable.exists()
    for _ in range(2):
        result = subprocess.run(
            [
                "bash", str(SCRIPTS / "ci.sh"), "runtime-readiness",
                "--probe-installed", sys.executable, str(executable),
                "postgresql://ea_runtime:bad@127.0.0.1:1/ea_core", "false",
            ],
            capture_output=True,
            text=True,
            check=False,
            cwd=tmp_path,
        )
        assert result.returncode == 0, result.stderr
        assert "installed-process readiness passed" in result.stdout
        assert not list(tmp_path.iterdir())
    text = (SCRIPTS / "runtime-readiness.sh").read_text()
    assert 'bind(("127.0.0.1", 0))' in text
    assert "process.terminate()" in text
    assert "process.wait(timeout=" in text
    assert "range(5)" in text
    assert "signal.signal(signal.SIGTERM, stop)" in text


def test_installed_process_failure_is_reported(tmp_path: Path) -> None:
    """Refuse to mask startup failure as an accepted negative readiness result."""
    import sys

    executable = tmp_path / "failed-service"
    executable.write_text("#!/bin/sh\nexit 7\n", encoding="utf-8")
    executable.chmod(0o755)
    result = subprocess.run(
        [
            "bash", str(SCRIPTS / "ci.sh"), "runtime-readiness",
            "--probe-installed", sys.executable, str(executable),
            "postgresql://ea_runtime:bad@127.0.0.1:1/ea_core", "false",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert "installed ea-core exited before health" in result.stderr


def test_cancelled_lane_reaps_its_installed_child(tmp_path: Path) -> None:
    """Forward shell cancellation and reap the running installed subprocess."""
    import signal
    import sys
    import time

    pid_file = tmp_path / "child-pid"
    executable = tmp_path / "waiting-service"
    executable.write_text(
        f"#!{sys.executable}\n"
        "import os, time\n"
        f"with open({str(pid_file)!r}, 'w') as output:\n"
        "    output.write(str(os.getpid()))\n"
        "time.sleep(60)\n",
        encoding="utf-8",
    )
    executable.chmod(0o755)
    process = subprocess.Popen(
        [
            "bash", str(SCRIPTS / "ci.sh"), "runtime-readiness",
            "--probe-installed", sys.executable, str(executable),
            "postgresql://ea_runtime:bad@127.0.0.1:1/ea_core", "false",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    child = None
    try:
        deadline = time.monotonic() + 10
        while not pid_file.exists() and time.monotonic() < deadline:
            time.sleep(0.05)
        assert pid_file.exists(), "installed process never started"
        child = int(pid_file.read_text())
        process.send_signal(signal.SIGTERM)
        assert process.wait(timeout=10) == 143
        try:
            os.kill(child, 0)
        except ProcessLookupError:
            pass
        else:
            raise AssertionError("cancelled lane leaked its installed process")
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()
        if child is not None:
            try:
                os.kill(child, signal.SIGTERM)
            except ProcessLookupError:
                pass


def test_workflows_delegate_execution_and_keep_source_checkout() -> None:
    """Delegate gates only after explicit inline source admission and checkout."""
    admission = (
        "    steps:\n"
        "      - name: Admit trusted source\n"
        "        env:\n"
        "          SOURCE_REPOSITORY: "
        "${{ github.event.pull_request.head.repo.full_name || github.repository }}\n"
        "          EXPECTED_REPOSITORY: ${{ github.repository }}\n"
        '        run: test "$SOURCE_REPOSITORY" = "$EXPECTED_REPOSITORY"\n'
        "      - uses: actions/checkout@"
    )
    ci = (ROOT / ".github/workflows/ci.yml").read_text()
    for lane in ("validate", "postgres-migration", "compose-runtime", "package"):
        assert f"bash .github/scripts/ci.sh {lane}" in ci
    runtime = (ROOT / ".github/workflows/runtime-readiness.yml").read_text()
    assert "bash .github/scripts/ci.sh runtime-readiness" in runtime
    supply_chain = (ROOT / ".github/workflows/supply-chain.yml").read_text()
    candidate_evidence, release = supply_chain.split("  attest-protected-main:")
    for text in (ci, runtime, candidate_evidence):
        assert text.count(admission) == text.count("    runs-on:")
        assert "    if:" not in text
        assert "ref: ${{ github.event.pull_request.head.sha || github.sha }}" in text
        assert text.count("persist-credentials: false") == text.count("    runs-on:")
        assert text.count("- name: Verify exact source checkout") == text.count(
            "    runs-on:"
        )
        assert "uv sync " not in text
        assert "docker compose " not in text
    assert (
        "if: github.event_name == 'push' && github.ref == 'refs/heads/main' "
        "&& github.ref_protected"
    ) in release
    assert "- 5432:5432" not in ci
    assert "PGPORT: ${{ job.services.postgres.ports['5432'] }}" in ci
    assert "path: ${{ env.CI_DIST }}" in ci