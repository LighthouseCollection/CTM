"""Run on VM as admin; creates isolated test role/db without exposing server passwords."""
import os
from pathlib import Path
import secrets
import subprocess

role='ctm_validation'
password=secrets.token_hex(32)
sql=f"""SELECT 'CREATE ROLE {role} LOGIN NOSUPERUSER NOBYPASSRLS CREATEDB PASSWORD ''{password}'''
WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname='{role}')\n\\gexec
ALTER ROLE {role} PASSWORD '{password}';
SELECT 'CREATE DATABASE ctm_validation OWNER {role}' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname='ctm_validation')\n\\gexec
"""
command=['docker','exec','-i','deploy-postgres-1','sh','-c','PGPASSWORD="$POSTGRES_PASSWORD" psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"']
result=subprocess.run(command,input=sql,text=True,capture_output=True)
if result.returncode:
    raise SystemExit('Isolated test DB setup failed; inspect locally without publishing credentials.')
target=Path('/opt/ctm-validation/test.env')
target.parent.mkdir(parents=True,exist_ok=True)
target.write_text(f'CTM_TEST_DATABASE_URL=postgres://{role}:{password}@deploy-postgres-1:5432/ctm_validation\nDJANGO_SECRET_KEY=isolated-validation-only\n')
target.chmod(0o600)
print('Isolated validation role/database prepared; credentials retained only in protected VM test.env.')
