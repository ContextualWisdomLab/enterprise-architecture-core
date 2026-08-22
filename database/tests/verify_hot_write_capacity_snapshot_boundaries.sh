#!/usr/bin/env bash
set -euo pipefail

psql_args=(
  --host 127.0.0.1
  --username ea_app
  --dbname ea_core
)
report_path="database/reports/hot_write_capacity_snapshot.sql"
tenant_id="0195d145-64e8-7f4f-8a23-a0cc784cb711"
probe_directory="$(mktemp -d)"
trap 'rm -rf "$probe_directory"' EXIT

# A standalone operator invocation begins with no caller tenant GUC. The report
# must take its RESET branch and must not leave the requested tenant installed.
psql "${psql_args[@]}" --set ON_ERROR_STOP=1 <<SQL
\set tenant_id '$tenant_id'
\i $report_path
SELECT COALESCE(
    NULLIF(pg_catalog.current_setting('app.tenant_record_id', true), ''),
    '<unset>'
) = '<unset>' AS cwl_capacity_context_restored \gset
\if :cwl_capacity_context_restored
\else
\echo 'hot-write snapshot left tenant context installed after standalone use'
SELECT 1 / 0;
\endif
SQL

missing_tenant_log="$probe_directory/missing-tenant.log"
if psql "${psql_args[@]}" --set ON_ERROR_STOP=1 \
  --file "$report_path" >"$missing_tenant_log" 2>&1; then
  echo "hot-write snapshot accepted a missing tenant_id" >&2
  exit 1
fi
grep --fixed-strings \
  'tenant_id is required: psql --set tenant_id=<uuid>' \
  "$missing_tenant_log"

failed_snapshot_log="$probe_directory/failed-snapshot.log"
if psql "${psql_args[@]}" --set ON_ERROR_STOP=1 \
  --set tenant_id=not-a-uuid \
  --file "$report_path" >"$failed_snapshot_log" 2>&1; then
  echo "hot-write snapshot accepted an invalid tenant as a successful report" >&2
  exit 1
fi
grep --fixed-strings \
  'hot-write capacity snapshot failed after restoring caller tenant context' \
  "$failed_snapshot_log"
