#!/usr/bin/env bash
set -euo pipefail
script_directory="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
lane="${1:-}"
shift || true
case "$lane" in
  validate|postgres-migration|compose-runtime|runtime-readiness|package)
    exec bash "$script_directory/$lane.sh" "$@"
    ;;
  *) printf 'unknown CI lane: %s\n' "$lane" >&2; exit 2 ;;
esac
