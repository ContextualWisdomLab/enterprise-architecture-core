#!/usr/bin/env bash
# Never consume persistent runner workspace evidence from earlier runs.
set -euo pipefail
: "${GITHUB_ENV:?GITHUB_ENV is required}"
umask 077
evidence="$(mktemp -d "${RUNNER_TEMP:-${TMPDIR:-/tmp}}/ea-evidence.XXXXXXXXXX")"
printf 'CI_EVIDENCE=%s\n' "$evidence" >> "$GITHUB_ENV"
