#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
ci_require_uv
PYTHON_VERSION="${1:-${PYTHON_VERSION:-3.14}}"
case "$PYTHON_VERSION" in
  3.11|3.12|3.13|3.14) ;;
  *) printf 'unsupported validation Python: %s\n' "$PYTHON_VERSION" >&2; exit 2 ;;
esac
ci_init validate
uv lock --check
uv sync --locked --extra dev --python "$PYTHON_VERSION"
run() { uv run --frozen --extra dev --python "$PYTHON_VERSION" "$@"; }
run python -m compileall -q src scripts .github/scripts
run python -m ruff check . --output-format=github
run python -m ruff check .github/tests --output-format=github
run python -m coverage run -m pytest -q tests .github/tests
run python -m coverage report
run python scripts/validate_repository.py
