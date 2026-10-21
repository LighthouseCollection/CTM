#!/usr/bin/env bash
set -euo pipefail

# Fresh-volume initialization only. Existing installations require a separately
# reviewed role migration; restarting Compose does not rerun init scripts.
if [ -z "${ENGRAM_DB_PASSWORD:-}" ]; then
    echo 'Optional Engram database omitted: dedicated credential not configured.'
    exit 0
fi
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" --set=engram_password="$ENGRAM_DB_PASSWORD" <<'SQL'
    SELECT format('CREATE ROLE engram_cloud LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD %L', :'engram_password')
    WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'engram_cloud')
    \gexec
    SELECT 'CREATE DATABASE engram_cloud OWNER engram_cloud'
    WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'engram_cloud')
    \gexec
    REVOKE CONNECT ON DATABASE engram_cloud FROM PUBLIC;
    GRANT CONNECT ON DATABASE engram_cloud TO engram_cloud;
SQL
