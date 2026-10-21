#!/usr/bin/env bash
set -euo pipefail

# Fresh-cluster role setup only. No existing role password is reset.
: "${CTM_APP_PASSWORD:?Set CTM_APP_PASSWORD}"
: "${CTM_WORKER_PASSWORD:?Set CTM_WORKER_PASSWORD}"
: "${POSTGRES_USER:?Set POSTGRES_USER}"
: "${POSTGRES_DB:?Set POSTGRES_DB}"
: "${POSTGRES_PASSWORD:?Set POSTGRES_PASSWORD}"

# -X ignores operator psqlrc files. Passwords remain out of argv and SQL assembly.
PGPASSWORD="$POSTGRES_PASSWORD" psql -X -v ON_ERROR_STOP=1 \
    --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
    --file "${CTM_INIT_SQL:-/usr/local/share/ctm/init.sql}"
echo "CTM roles and extensions initialized."
