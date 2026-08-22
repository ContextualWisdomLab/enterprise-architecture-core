#!/usr/bin/env bash
set -euo pipefail

: "${EA_RUNTIME_PASSWORD:?EA_RUNTIME_PASSWORD is required}"

psql \
  --variable ON_ERROR_STOP=1 \
  --username "$POSTGRES_USER" \
  --dbname "$POSTGRES_DB" \
  --set=runtime_password="$EA_RUNTIME_PASSWORD" <<'SQL'
SELECT format(
    'CREATE ROLE ea_runtime LOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD %L',
    :'runtime_password'
)
WHERE NOT EXISTS (
    SELECT 1
      FROM pg_catalog.pg_roles
     WHERE rolname = 'ea_runtime'
) \gexec

ALTER ROLE ea_runtime
    LOGIN
    NOINHERIT
    NOSUPERUSER
    NOCREATEDB
    NOCREATEROLE
    NOREPLICATION
    NOBYPASSRLS
    PASSWORD :'runtime_password';
SQL
