#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
probe_installed() {
  local python="$1" executable="$2" dsn="$3" expected="$4"
  "$python" - "$executable" "$dsn" "$expected" "$CI_TEMP" <<'PY' &
import json
import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

executable, dsn, expected, directory = sys.argv[1:]
def stop(signum, frame):
    raise SystemExit(128 + signum)
signal.signal(signal.SIGTERM, stop)
signal.signal(signal.SIGINT, stop)
# main rejects PORT=0 and does not publish its selected port. Reserve an
# ephemeral candidate and retry only a diagnosed bind race; no source patch.
for attempt in range(5):
    with socket.socket() as candidate:
        candidate.bind(("127.0.0.1", 0))
        port = candidate.getsockname()[1]
    environment = dict(os.environ, EA_BIND_HOST="127.0.0.1", PORT=str(port),
                       EA_DATABASE_DSN=dsn)
    log = Path(directory) / f"runtime-{attempt}.log"
    with log.open("w+") as output:
        process = subprocess.Popen([executable], env=environment,
                                   cwd=directory, stdout=output,
                                   stderr=subprocess.STDOUT)
        retry_bind = False
        try:
            deadline = time.monotonic() + 30
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    output.seek(0)
                    message = output.read()
                    if "Address already in use" in message:
                        retry_bind = True
                        break
                    raise AssertionError("installed ea-core exited before health")
                try:
                    with urlopen(f"http://127.0.0.1:{port}/health", timeout=2) as response:
                        assert response.status == 200
                        json.loads(response.read())
                    break
                except (URLError, TimeoutError, ConnectionError):
                    time.sleep(0.1)
            else:
                raise AssertionError("installed ea-core never became healthy")
            if not retry_bind:
                assert process.poll() is None, "installed ea-core exited"
                try:
                    urlopen(f"http://127.0.0.1:{port}/ready", timeout=10)
                except HTTPError as error:
                    assert error.code == 503
                    payload = json.loads(error.read())
                else:
                    raise AssertionError("unreleased contract passed readiness")
                assert payload["database_ready"] is (expected == "true"), payload
                assert payload["contract_ready"] is False, payload
                print("installed-process readiness passed")
        finally:
            if process.poll() is None:
                process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
    if not retry_bind:
        break
else:
    raise AssertionError("installed ea-core exhausted ephemeral bind retries")
PY
  probe_pid=$!
  trap 'kill -TERM "$probe_pid" 2>/dev/null || true; wait "$probe_pid" 2>/dev/null || true; exit 130' INT
  trap 'kill -TERM "$probe_pid" 2>/dev/null || true; wait "$probe_pid" 2>/dev/null || true; exit 143' TERM
  local status=0
  wait "$probe_pid" || status=$?
  trap 'exit 130' INT
  trap 'exit 143' TERM
  return "$status"
}
if [[ "${1:-}" == --probe-installed ]]; then
  [[ $# -eq 5 ]] || { printf 'expected python, executable, DSN, expected database state\n' >&2; exit 2; }
  ci_require "$2" "$3"
  ci_init runtime-probe
  probe_installed "$2" "$3" "$4" "$5"
  exit
fi
ci_require_uv
ci_require docker psql
ci_init runtime-readiness
ci_start_database
PYTHON_VERSION="${PYTHON_VERSION:-3.14}"
uv lock --check
uv sync --locked --extra dev --python "$PYTHON_VERSION"
uv build --wheel --out-dir "$CI_TEMP/dist"
uv venv "$CI_TEMP/runtime" --python "$PYTHON_VERSION"
uv pip install --python "$CI_TEMP/runtime/bin/python" \
  --no-index --find-links "$CI_TEMP/dist" enterprise-architecture-core
runtime_dsn="$(sed -n 's/^EA_DATABASE_DSN=//p' .env.example)"
runtime_dsn="${runtime_dsn/change-me-runtime/$EA_RUNTIME_PASSWORD}"
runtime_dsn="${runtime_dsn/:54328\//:$CI_DATABASE_PORT/}"
probe_installed "$CI_TEMP/runtime/bin/python" "$CI_TEMP/runtime/bin/ea-core" "$runtime_dsn" true
bad_dsn="${runtime_dsn/$EA_RUNTIME_PASSWORD/incorrect-ci-password}"
probe_installed "$CI_TEMP/runtime/bin/python" "$CI_TEMP/runtime/bin/ea-core" "$bad_dsn" false
