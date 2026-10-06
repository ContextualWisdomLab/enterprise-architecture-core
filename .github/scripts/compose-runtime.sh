#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
ci_init compose-runtime
ci_start_database
runtime_dsn="$(sed -n 's/^EA_DATABASE_DSN=//p' .env.example)"
runtime_dsn="${runtime_dsn/change-me-runtime/$EA_RUNTIME_PASSWORD}"
runtime_dsn="${runtime_dsn/:54328\//:$CI_DATABASE_PORT/}"
psql "$runtime_dsn" --set ON_ERROR_STOP=1 \
  --file database/acceptance/runtime/verify_runtime_role.sql
