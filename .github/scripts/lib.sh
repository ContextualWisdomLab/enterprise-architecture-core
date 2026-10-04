#!/usr/bin/env bash
# Shared helpers never acquire resources until the lane calls ci_init.
ci_require() {
  local executable
  for executable in "$@"; do
    if ! command -v "$executable" >/dev/null 2>&1; then
      printf 'CI prerequisite missing: %s\n' "$executable" >&2
      return 1
    fi
  done
}
ci_require_uv() {
  ci_require uv
  local version
  version="$(uv --version)"
  if [[ "$version" != 'uv 0.11.32' && "$version" != 'uv 0.11.32 '* ]]; then
    printf 'CI requires uv 0.11.32; found %s\n' "$version" >&2
    return 1
  fi
}
ci_init() {
  local lane="$1"
  CI_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
  cd "$CI_ROOT" || return
  CI_TEMP="$(mktemp -d "${TMPDIR:-/tmp}/ea-core-${lane}.XXXXXXXXXX")"
  CI_TEMP="$(cd "$CI_TEMP" && pwd)"
  export UV_PROJECT_ENVIRONMENT="$CI_TEMP/venv"
  export COVERAGE_FILE="$CI_TEMP/.coverage"
  trap 'rm -rf "$CI_TEMP"' EXIT
  trap 'exit 130' INT
  trap 'exit 143' TERM
}
ci_compose() {
  docker compose --project-name "$CI_PROJECT" --file "$CI_ROOT/.github/compose.ci.yaml" "$@"
}
ci_compose_cleanup() {
  local status=$?
  trap - EXIT
  if ! ci_compose down --volumes --remove-orphans; then
    printf 'CI compose cleanup failed for %s\n' "$CI_PROJECT" >&2
    status=1
  fi
  rm -rf "$CI_TEMP"
  exit "$status"
}
ci_start_database() {
  ci_require docker psql
  docker compose version >/dev/null
  docker info >/dev/null
  : "${EA_OWNER_PASSWORD:?EA_OWNER_PASSWORD is required}"
  : "${EA_RUNTIME_PASSWORD:?EA_RUNTIME_PASSWORD is required}"
  CI_PROJECT="ea-core-$(basename "$CI_TEMP" | tr '[:upper:].' '[:lower:]-')"
  trap ci_compose_cleanup EXIT
  if ! ci_compose up --detach --wait; then
    ci_compose ps --all || true
    ci_compose logs --no-color || true
    return 1
  fi
  local published
  published="$(ci_compose port architecture_database 5432)"
  CI_DATABASE_PORT="${published##*:}"
  if [[ ! "$CI_DATABASE_PORT" =~ ^[0-9]+$ ]]; then
    printf 'Could not discover CI database port\n' >&2
    return 1
  fi
  export PGHOST=127.0.0.1 PGPORT="$CI_DATABASE_PORT" PGUSER=ea_owner PGDATABASE=ea_core
  PGPASSWORD="$EA_OWNER_PASSWORD" psql --set ON_ERROR_STOP=1 \
    --file database/acceptance/runtime/prepare_runtime_fixture.sql
}
