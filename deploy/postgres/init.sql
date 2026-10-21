-- CTM PostgreSQL initialization
-- Called by 00-init-roles.sh which injects passwords via psql -v flags.
-- Django migrations own all application tables; this script creates
-- only extensions and restricted runtime roles.

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'ctm_app') THEN
        EXECUTE format('CREATE ROLE ctm_app LOGIN PASSWORD %L', :'ctm_app_pw');
    END IF;
END
$$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'ctm_worker') THEN
        EXECUTE format('CREATE ROLE ctm_worker LOGIN PASSWORD %L', :'ctm_worker_pw');
    END IF;
END
$$;

ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON TABLES FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO ctm_app, ctm_worker;
