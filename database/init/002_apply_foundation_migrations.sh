#!/usr/bin/env bash
set -euo pipefail

for migration_path in /opt/ea-core/migrations/*.sql; do
  psql \
    --variable ON_ERROR_STOP=1 \
    --username "$POSTGRES_USER" \
    --dbname "$POSTGRES_DB" \
    --file "$migration_path"
done
