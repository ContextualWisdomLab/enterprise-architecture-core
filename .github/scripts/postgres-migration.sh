#!/usr/bin/env bash
set -euo pipefail
# Fixture dependencies require bytewise ordering on every runner locale.
export LC_ALL=C
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
if (( BASH_VERSINFO[0] < 4 )); then
  printf 'postgres-migration requires Bash 4 or newer\n' >&2
  exit 1
fi
ci_require psql sha256sum find sort sed head tail awk cp grep
: "${PGHOST:?PGHOST is required}" "${PGPORT:?PGPORT is required}" "${PGUSER:?PGUSER is required}"
ci_init postgres-migration
database_suffix="$(basename "$CI_TEMP" | tr -cd '[:alnum:]' | tr '[:upper:]' '[:lower:]')"
export PGDATABASE="ea_core_ci_${database_suffix}"
probe_databases=()
cleanup() {
  local status=$?
  trap - EXIT
  local database
  for database in "${probe_databases[@]}"; do
    if ! psql --dbname postgres --set ON_ERROR_STOP=1 --command "DROP DATABASE IF EXISTS ${database};"; then
      status=1
    fi
  done
  rm -rf "$CI_TEMP"
  exit "$status"
}
trap cleanup EXIT
psql --dbname postgres --set ON_ERROR_STOP=1 --command "CREATE DATABASE ${PGDATABASE};"
probe_databases+=("$PGDATABASE")
bash database/scripts/apply_migrations.sh database/migrations
bash database/scripts/apply_migrations.sh database/migrations
drift_directory="$(mktemp -d "$CI_TEMP/drift_directory.XXXXXXXXXX")"
cp database/migrations/*.sql "$drift_directory/"
# Change bytes inside the exact transaction wrappers so failure proves drift,
# rather than merely rejecting a malformed migration file.
sed '$d' database/migrations/0001_identity_objects.sql > "$drift_directory/0001_identity_objects.sql"
printf '\n-- checksum drift acceptance probe\nCOMMIT;\n' \
  >> "$drift_directory/0001_identity_objects.sql"
if bash database/scripts/apply_migrations.sh "$drift_directory" > "$CI_TEMP/drift.log" 2>&1; then
  echo "checksum drift was unexpectedly accepted" >&2
  exit 1
fi
grep --fixed-strings 'applied migration checksum mismatch' "$CI_TEMP/drift.log"

probe_database="ea_core_upgrade_${database_suffix}"
prior_directory="$(mktemp -d "$CI_TEMP/prior_directory.XXXXXXXXXX")"
psql --dbname postgres --set ON_ERROR_STOP=1 \
  --command "CREATE DATABASE ${probe_database};"
probe_databases+=("$probe_database")
mapfile -t migration_paths < <(
  find database/migrations -maxdepth 1 -type f \
    -name '[0-9][0-9][0-9][0-9]_*.sql' -print | sort
)
if [ "${#migration_paths[@]}" -lt 2 ]; then
  echo "upgrade rehearsal requires at least two migrations" >&2
  exit 1
fi
latest_index=$((${#migration_paths[@]} - 1))
for ((index = 0; index < latest_index; index++)); do
  cp "${migration_paths[$index]}" "$prior_directory/"
done
PGDATABASE="$probe_database" \
  bash database/scripts/apply_migrations.sh "$prior_directory"
prior_ledger_count="$(
  PGDATABASE="$probe_database" psql --tuples-only --no-align \
    --set ON_ERROR_STOP=1 \
    --command "SELECT count(*) FROM architecture_core.schema_migration_record;"
)"
test "$prior_ledger_count" -eq "$latest_index"
PGDATABASE="$probe_database" \
  bash database/scripts/apply_migrations.sh database/migrations
upgraded_ledger_count="$(
  PGDATABASE="$probe_database" psql --tuples-only --no-align \
    --set ON_ERROR_STOP=1 \
    --command "SELECT count(*) FROM architecture_core.schema_migration_record;"
)"
test "$upgraded_ledger_count" -eq "${#migration_paths[@]}"
PGDATABASE="$probe_database" psql --tuples-only --no-align \
  --set ON_ERROR_STOP=1 \
  --command "SELECT conname FROM pg_constraint WHERE conname IN ('object_revision_evidence_required', 'architecture_relation_evidence_required') ORDER BY conname;" \
  | grep --fixed-strings 'architecture_relation_evidence_required'
PGDATABASE="$probe_database" psql --tuples-only --no-align \
  --set ON_ERROR_STOP=1 \
  --command "SELECT conname FROM pg_constraint WHERE conname IN ('object_revision_evidence_required', 'architecture_relation_evidence_required') ORDER BY conname;" \
  | grep --fixed-strings 'object_revision_evidence_required'
PGDATABASE="$probe_database" psql --tuples-only --no-align \
  --set ON_ERROR_STOP=1 \
  --command "SELECT conname FROM pg_constraint WHERE conname IN ('outbox_event_publish_chronology', 'projection_receipt_process_chronology') ORDER BY conname;" \
  | grep --fixed-strings 'outbox_event_publish_chronology'
PGDATABASE="$probe_database" psql --tuples-only --no-align \
  --set ON_ERROR_STOP=1 \
  --command "SELECT conname FROM pg_constraint WHERE conname IN ('outbox_event_publish_chronology', 'projection_receipt_process_chronology') ORDER BY conname;" \
  | grep --fixed-strings 'projection_receipt_process_chronology'
PGDATABASE="$probe_database" psql --tuples-only --no-align \
  --set ON_ERROR_STOP=1 \
  --command "SELECT to_regclass('architecture_core.object_assessment') IS NOT NULL;" \
  | grep --fixed-strings 't'
PGDATABASE="$probe_database" psql --tuples-only --no-align \
  --set ON_ERROR_STOP=1 \
  --command "SELECT to_regclass('architecture_core.strategy_objective') IS NOT NULL;" \
  | grep --fixed-strings 't'
PGDATABASE="$probe_database" psql --tuples-only --no-align \
  --set ON_ERROR_STOP=1 \
  --command "SELECT to_regclass('architecture_core.architecture_scenario') IS NOT NULL;" \
  | grep --fixed-strings 't'
PGDATABASE="$probe_database" psql --tuples-only --no-align \
  --set ON_ERROR_STOP=1 \
  --command "SELECT to_regclass('architecture_core.scenario_relation_delta') IS NOT NULL;" \
  | grep --fixed-strings 't'
PGDATABASE="$probe_database" psql --tuples-only --no-align \
  --set ON_ERROR_STOP=1 \
  --command "SELECT to_regprocedure('architecture_core.project_scenario_relations(uuid)') IS NOT NULL;" \
  | grep --fixed-strings 't'
PGDATABASE="$probe_database" psql --tuples-only --no-align \
  --set ON_ERROR_STOP=1 \
  --command "SELECT to_regclass('architecture_core.architecture_transformation') IS NOT NULL;" \
  | grep --fixed-strings 't'
PGDATABASE="$probe_database" psql --tuples-only --no-align \
  --set ON_ERROR_STOP=1 \
  --command "SELECT to_regclass('architecture_core.transformation_history_record') IS NOT NULL;" \
  | grep --fixed-strings 't'
PGDATABASE="$probe_database" psql --tuples-only --no-align \
  --set ON_ERROR_STOP=1 \
  --command "SELECT to_regprocedure('architecture_core.project_transformation_state(uuid,timestamp with time zone,timestamp with time zone)') IS NOT NULL;" \
  | grep --fixed-strings 't'
PGDATABASE="$probe_database" psql --tuples-only --no-align \
  --set ON_ERROR_STOP=1 \
  --command "SELECT to_regprocedure('architecture_core.project_technology_change_impact(uuid,timestamp with time zone,timestamp with time zone,integer)') IS NOT NULL;" \
  | grep --fixed-strings 't'

probe_database="ea_core_atomicity_${database_suffix}"
probe_directory="$(mktemp -d "$CI_TEMP/probe_directory.XXXXXXXXXX")"
psql --dbname postgres --set ON_ERROR_STOP=1 \
  --command "CREATE DATABASE ${probe_database};"
probe_databases+=("$probe_database")
cp database/migrations/0001_identity_objects.sql "$probe_directory/"
sed '$d' database/migrations/0001_identity_objects.sql > "$probe_directory/0001_identity_objects.sql"
printf 'SELECT 1 / 0;\nCOMMIT;\n' >> "$probe_directory/0001_identity_objects.sql"
if PGDATABASE="$probe_database" \
   bash database/scripts/apply_migrations.sh "$probe_directory"; then
  echo "failing migration unexpectedly committed" >&2
  exit 1
fi
schema_absent="$(
  PGDATABASE="$probe_database" psql --tuples-only --no-align \
    --set ON_ERROR_STOP=1 \
    --command "SELECT to_regnamespace('architecture_core') IS NULL;"
)"
test "$schema_absent" = "t"

table_count="$(
  psql \
    --tuples-only --no-align \
    --command "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'architecture_core' AND table_type = 'BASE TABLE';"
)"
test "$table_count" -eq 36
reference_view_count="$(
  psql \
    --tuples-only --no-align \
    --command "SELECT count(*) FROM information_schema.views WHERE table_schema = 'architecture_core' AND table_name = 'architecture_object_reference';"
)"
test "$reference_view_count" -eq 1
ledger_count="$(
  psql \
    --tuples-only --no-align \
    --command "SELECT count(*) FROM architecture_core.schema_migration_record;"
)"
test "$ledger_count" -eq 15

for acceptance_path in database/tests/*.sql; do
  psql \
    --set ON_ERROR_STOP=1 --file "$acceptance_path"
done
