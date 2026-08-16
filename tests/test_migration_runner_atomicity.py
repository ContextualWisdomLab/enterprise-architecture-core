"""Executable regression for atomic migration and checksum-ledger commits."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess


def _write_fake_psql(fake_path: Path) -> None:
    """Create a deterministic psql double that records transaction boundaries."""
    fake_path.write_text(
        """#!/usr/bin/env python3
import json
import os
from pathlib import Path
import sys

args = sys.argv[1:]
state_path = Path(os.environ[\"FAKE_PSQL_STATE\"])
log_path = Path(os.environ[\"FAKE_PSQL_LOG\"])
command = next(
    (args[index + 1] for index, value in enumerate(args[:-1]) if value == \"--command\"),
    None,
)
file_path = next(
    (args[index + 1] for index, value in enumerate(args[:-1]) if value == \"--file\"),
    None,
)
stdin_text = sys.stdin.read()

if command and \"to_regclass('architecture_core.schema_migration_record')\" in command:
    print(\"t\" if state_path.exists() else \"f\")
    raise SystemExit(0)

body = stdin_text
mode = \"stdin\"
if file_path is not None:
    body = Path(file_path).read_text(encoding=\"utf-8\")
    mode = \"file\"

if \"SELECT migration_sha256\" in body:
    if state_path.exists():
        print(state_path.read_text(encoding=\"utf-8\"))
    raise SystemExit(0)

if body:
    with log_path.open(\"a\", encoding=\"utf-8\") as log_file:
        log_file.write(json.dumps({\"mode\": mode, \"body\": body}) + \"\\n\")
    if \"CREATE TABLE architecture_core.schema_migration_record\" in body:
        state_path.write_text(\"ledger-created\", encoding=\"utf-8\")
    if \"INSERT INTO architecture_core.schema_migration_record\" in body:
        digest = next(
            (
                args[index + 1]
                for index, value in enumerate(args[:-1])
                if value == \"--set\" and args[index + 1].startswith(\"migration_sha256=\")
            ),
            \"migration_sha256=unknown\",
        ).split(\"=\", 1)[1]
        state_path.write_text(digest, encoding=\"utf-8\")

raise SystemExit(0)
""",
        encoding="utf-8",
    )
    fake_path.chmod(0o755)


def test_runner_commits_schema_and_ledger_in_one_database_transaction(
    repository_root: Path, tmp_path: Path
) -> None:
    """A crash boundary cannot leave committed DDL without its checksum record."""
    migration_directory = tmp_path / "migrations"
    migration_directory.mkdir()
    (migration_directory / "0001_atomic_probe.sql").write_text(
        """BEGIN;
CREATE SCHEMA architecture_core;
CREATE TABLE architecture_core.schema_migration_record (
    migration_name text NOT NULL,
    migration_sha256 text NOT NULL
);
CREATE TABLE architecture_core.atomic_probe (probe_value text);
COMMIT;
""",
        encoding="utf-8",
    )

    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_psql = fake_bin / "psql"
    _write_fake_psql(fake_psql)
    state_path = tmp_path / "psql-state"
    log_path = tmp_path / "psql-log.jsonl"
    environment = os.environ.copy()
    environment["PATH"] = f"{fake_bin}{os.pathsep}{environment['PATH']}"
    environment["FAKE_PSQL_STATE"] = str(state_path)
    environment["FAKE_PSQL_LOG"] = str(log_path)

    result = subprocess.run(
        [
            "bash",
            str(repository_root / "database/scripts/apply_migrations.sh"),
            str(migration_directory),
        ],
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )

    assert result.returncode == 0, result.stderr
    invocations = [
        json.loads(line)
        for line in log_path.read_text(encoding="utf-8").splitlines()
        if line
    ]
    atomic_invocations = [
        invocation
        for invocation in invocations
        if "CREATE TABLE architecture_core.schema_migration_record"
        in invocation["body"]
        and "INSERT INTO architecture_core.schema_migration_record"
        in invocation["body"]
    ]
    assert len(atomic_invocations) == 1
    atomic_body = atomic_invocations[0]["body"]
    assert atomic_invocations[0]["mode"] == "stdin"
    assert atomic_body.index("BEGIN;") < atomic_body.index(
        "CREATE TABLE architecture_core.schema_migration_record"
    )
    assert atomic_body.index(
        "INSERT INTO architecture_core.schema_migration_record"
    ) < atomic_body.rindex("COMMIT;")
