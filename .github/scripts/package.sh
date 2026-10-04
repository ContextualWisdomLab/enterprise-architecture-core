#!/usr/bin/env bash
# Build fresh distributions and smoke-test the installed wheel.
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$root"
python_version="${PYTHON_VERSION:-3.14}"
command -v uv >/dev/null
uv lock --check
work="$(mktemp -d "${RUNNER_TEMP:-${TMPDIR:-/tmp}}/ea-package.XXXXXX")"
keep=false
cleanup() {
  if [ "$keep" = true ]; then
    rm -rf "$work/smoke"
  else
    rm -rf "$work"
  fi
}
trap cleanup EXIT
SOURCE_DATE_EPOCH="$(git show -s --format=%ct HEAD)"
export SOURCE_DATE_EPOCH
uv build --wheel --sdist --out-dir "$work/dist" --python "$python_version"
uv venv "$work/smoke" --python "$python_version"
uv pip install --python "$work/smoke/bin/python" --no-deps \
  --no-index --find-links "$work/dist" enterprise-architecture-core
(cd "$work" && "$work/smoke/bin/python" -I - "$root" "$work/dist" <<'PY'
from importlib.metadata import version
from importlib.util import find_spec
from pathlib import Path
import sys
import tomllib

import ea_core_foundation

project = tomllib.loads((Path(sys.argv[1]) / "pyproject.toml").read_text())
expected = project["project"]["version"]
assert version("enterprise-architecture-core") == expected
assert ea_core_foundation.__version__ == expected
assert Path(ea_core_foundation.__file__).resolve().is_relative_to(Path(sys.prefix).resolve())
assert find_spec("jsonschema") is None
assert len(list(Path(sys.argv[2]).glob("*.whl"))) == 1
assert len(list(Path(sys.argv[2]).glob("*.tar.gz"))) == 1
print("installed package smoke: OK")
PY
)
if [ -n "${GITHUB_ENV:-}" ]; then
  printf 'CI_DIST=%s\n' "$work/dist" >> "$GITHUB_ENV"
fi
printf 'Fresh distribution directory: %s\n' "$work/dist"
keep=true
