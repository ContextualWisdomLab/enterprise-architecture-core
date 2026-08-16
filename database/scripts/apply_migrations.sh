#!/usr/bin/env bash
set -euo pipefail

migration_directory="${1:-/opt/ea-core/migrations}"

if [[ ! -d "$migration_directory" ]]; then
  printf 'migration directory does not exist: %s\n' "$migration_directory" >&2
  exit 1
fi

mapfile -t migration_paths < <(
  find "$migration_directory" -maxdepth 1 -type f -name '*.sql' -print | sort
)

if [[ "${#migration_paths[@]}" -eq 0 ]]; then
  printf 'no migration files found in: %s\n' "$migration_directory" >&2
  exit 1
fi

expected_ordinal=1
for migration_path in "${migration_paths[@]}"; do
  migration_name="$(basename "$migration_path")"
  expected_prefix="$(printf '%04d_' "$expected_ordinal")"

  if [[ ! "$migration_name" =~ ^[0-9]{4}_[a-z][a-z0-9_]*\.sql$ ]]; then
    printf 'non-canonical migration filename: %s\n' "$migration_name" >&2
    exit 1
  fi
  if [[ "$migration_name" != "$expected_prefix"* ]]; then
    printf 'migration sequence gap: expected %s, found %s\n' \
      "$expected_prefix" "$migration_name" >&2
    exit 1
  fi

  migration_sha256="$(sha256sum "$migration_path" | awk '{print $1}')"
  ledger_exists="$(
    psql --tuples-only --no-align --set ON_ERROR_STOP=1 \
      --command "SELECT to_regclass('architecture_core.schema_migration_record') IS NOT NULL;"
  )"

  if [[ "$ledger_exists" == "t" ]]; then
    recorded_sha256="$(
      psql --tuples-only --no-align --set ON_ERROR_STOP=1 \
        --set migration_name="$migration_name" \
        --command "SELECT migration_sha256 FROM architecture_core.schema_migration_record WHERE migration_name = :'migration_name';"
    )"
    if [[ -n "$recorded_sha256" ]]; then
      if [[ "$recorded_sha256" != "$migration_sha256" ]]; then
        printf 'applied migration checksum mismatch: %s\n' "$migration_name" >&2
        exit 1
      fi
      printf 'verified applied migration: %s\n' "$migration_name"
      expected_ordinal=$((expected_ordinal + 1))
      continue
    fi
  fi

  psql --set ON_ERROR_STOP=1 --file "$migration_path"

  ledger_exists="$(
    psql --tuples-only --no-align --set ON_ERROR_STOP=1 \
      --command "SELECT to_regclass('architecture_core.schema_migration_record') IS NOT NULL;"
  )"
  if [[ "$ledger_exists" != "t" ]]; then
    printf 'migration did not establish checksum ledger: %s\n' "$migration_name" >&2
    exit 1
  fi

  psql --set ON_ERROR_STOP=1 \
    --set migration_name="$migration_name" \
    --set migration_sha256="$migration_sha256" \
    --command "INSERT INTO architecture_core.schema_migration_record (migration_name, migration_sha256) VALUES (:'migration_name', :'migration_sha256');"

  printf 'applied migration: %s\n' "$migration_name"
  expected_ordinal=$((expected_ordinal + 1))
done
