#!/usr/bin/env bash
set -euo pipefail

export PGUSER="$POSTGRES_USER"
export PGDATABASE="$POSTGRES_DB"

bash /opt/ea-core/scripts/apply_migrations.sh /opt/ea-core/migrations
