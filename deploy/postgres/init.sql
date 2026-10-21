-- Canonical fresh-cluster initialization. psql16 reads secrets from environment.
-- Values are quoted by psql and format(%L), never spliced into a DO body.
\set ON_ERROR_STOP on
\getenv ctm_app_pw CTM_APP_PASSWORD
\getenv ctm_worker_pw CTM_WORKER_PASSWORD
\getenv ctm_database POSTGRES_DB

BEGIN;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

SELECT format('CREATE ROLE ctm_app LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS NOINHERIT PASSWORD %L', :'ctm_app_pw')
WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'ctm_app')
\gexec
SELECT format('CREATE ROLE ctm_worker LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS NOINHERIT PASSWORD %L', :'ctm_worker_pw')
WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'ctm_worker')
\gexec

ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON TABLES FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO ctm_app, ctm_worker;
REVOKE CONNECT ON DATABASE :"ctm_database" FROM PUBLIC;
GRANT CONNECT ON DATABASE :"ctm_database" TO ctm_app, ctm_worker;
COMMIT;
