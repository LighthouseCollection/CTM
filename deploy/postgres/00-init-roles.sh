#!/usr/bin/env bash
set -euo pipefail

# Docker entrypoint runs .sh files in docker-entrypoint-initdb.d as shell.
# This handles all initialization: extensions, roles, and default privileges.
# Passwords come from environment variables set in docker-compose.yml.
# Single quotes in passwords are escaped to '' for safe SQL interpolation.

SAFE_APP_PW="${CTM_APP_PASSWORD//\'/\'\'}"
SAFE_WORKER_PW="${CTM_WORKER_PASSWORD//\'/\'\'}"

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
    CREATE EXTENSION IF NOT EXISTS "pgcrypto";
    CREATE EXTENSION IF NOT EXISTS "pg_trgm";

    DO \$\$
    BEGIN
        IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'ctm_app') THEN
            CREATE ROLE ctm_app LOGIN PASSWORD '${SAFE_APP_PW}';
        END IF;
        IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'ctm_worker') THEN
            CREATE ROLE ctm_worker LOGIN PASSWORD '${SAFE_WORKER_PW}';
        END IF;
    END
    \$\$;

    ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON TABLES FROM PUBLIC;
    GRANT USAGE ON SCHEMA public TO ctm_app, ctm_worker;
    REVOKE CONNECT ON DATABASE "$POSTGRES_DB" FROM PUBLIC;
    GRANT CONNECT ON DATABASE "$POSTGRES_DB" TO ctm_app, ctm_worker;
EOSQL

echo "CTM roles and extensions initialized."
