"""Provision only NOLOGIN roles for isolated PostgreSQL RLS tests."""

import subprocess

sql = """SELECT 'CREATE ROLE ctm_validation_runtime NOLOGIN NOSUPERUSER NOBYPASSRLS NOINHERIT' WHERE NOT EXISTS(SELECT FROM pg_roles WHERE rolname='ctm_validation_runtime')
\\gexec
GRANT ctm_validation_runtime TO ctm_validation;
"""
command = [
    "docker",
    "exec",
    "-i",
    "deploy-postgres-1",
    "sh",
    "-c",
    'PGPASSWORD="$POSTGRES_PASSWORD" psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"',
]
result = subprocess.run(command, input=sql, text=True, capture_output=True)
if result.returncode:
    raise SystemExit("Isolated role provisioning failed; no credentials printed.")
print("Non-owner NOLOGIN test role provisioned.")
