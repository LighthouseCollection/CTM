"""QA-01: create a disposable PostgreSQL database with separate owner and runtime roles.

Run against a throwaway local container only (loopback). Generated passwords are kept
in a local secrets file outside the repository and are never printed.

Roles (mirroring deploy/postgres/init.sql):
  qa_owner  - LOGIN, NOSUPERUSER, NOBYPASSRLS; owns the database and runs migrations.
  ctm_app   - LOGIN, NOSUPERUSER, NOBYPASSRLS, NOINHERIT; the HTTP runtime role.
  ctm_worker- LOGIN, NOSUPERUSER, NOBYPASSRLS, NOINHERIT; created so migrations see it.

Usage:
  python bootstrap_db.py create   # roles + database + extensions (before migrate)
  python bootstrap_db.py grant    # runtime table grants (after migrate)
"""

import json
import os
import secrets
import sys
from pathlib import Path

import psycopg
from psycopg import sql

from qa_env import EVIDENCE, SECRETS_DIR, load_env, save_env

DB = "ctm_qa01"
HOST, PORT = "127.0.0.1", int(os.environ.get("QA01_PG_PORT", "55433"))  # loopback-only disposable container


def superuser(dbname="postgres"):
    password = (SECRETS_DIR / "pg_super").read_text().strip()
    return psycopg.connect(host=HOST, port=PORT, user="qa_super", password=password,
                           dbname=dbname, autocommit=True)


def create():
    env = {}
    try:
        previous = load_env()
    except FileNotFoundError:
        previous = {}
    with superuser() as conn:
        for role, extra in [("qa_owner", "NOINHERIT"), ("ctm_app", "NOINHERIT"), ("ctm_worker", "NOINHERIT")]:
            # Reuse this machine's generated test password so a running server keeps working after reset.
            password = previous[role].split(":")[2].split("@")[0] if role in previous else secrets.token_hex(24)
            exists = conn.execute("SELECT 1 FROM pg_roles WHERE rolname=%s", [role]).fetchone()
            verb = "ALTER" if exists else "CREATE"
            conn.execute(sql.SQL(
                verb + " ROLE {} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS "
                + extra + " PASSWORD {}").format(sql.Identifier(role), sql.Literal(password)))
            env[role] = f"postgres://{role}:{password}@{HOST}:{PORT}/{DB}"
        conn.execute(sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(DB)))
        conn.execute(sql.SQL("CREATE DATABASE {} OWNER qa_owner").format(sql.Identifier(DB)))
    with superuser(DB) as conn:
        for ext in ["uuid-ossp", "pgcrypto", "pg_trgm"]:
            conn.execute(sql.SQL("CREATE EXTENSION IF NOT EXISTS {}").format(sql.Identifier(ext)))
        conn.execute(sql.SQL("REVOKE CONNECT ON DATABASE {} FROM PUBLIC").format(sql.Identifier(DB)))
        conn.execute(sql.SQL("GRANT CONNECT ON DATABASE {} TO qa_owner, ctm_app, ctm_worker").format(sql.Identifier(DB)))
        conn.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON TABLES FROM PUBLIC")
        conn.execute("GRANT USAGE ON SCHEMA public TO ctm_app, ctm_worker")
    save_env(env)
    print("Disposable database and roles created; credentials stored outside the repository.")


# Function entry points that tests/test_row_security.py grants to its runtime role.
FIXTURE_FUNCTIONS = [
    "ctm_source_readable(text,jsonb)", "ctm_source_writable(text,jsonb)",
    "ctm_source_mutable(text,jsonb)", "ctm_source_deletable(text,jsonb)",
    "ctm_paid_filing_actor(uuid)", "ctm_council_visible()", "ctm_council_writable(text,jsonb,text)",
    "ctm_council_mutable(text,jsonb)", "ctm_decision_readable(text,jsonb)",
    "ctm_decision_writable(text,jsonb)", "ctm_decree_writable(jsonb)",
    "ctm_finance_readable(text,jsonb)", "ctm_review_readable(jsonb)",
    "ctm_finance_writable(text,jsonb)", "ctm_finance_notice(text,jsonb)", "ctm_fee_can_waive(uuid)",
    "ctm_session_transfer_context(uuid)", "ctm_testimony_readable(text,jsonb)",
    "ctm_testimony_writable(text,jsonb)", "ctm_invitation_context(uuid)",
    "ctm_returned_source_visible(text,jsonb)", "ctm_library_readable(text,jsonb)",
    "ctm_library_writable(text,jsonb)", "ctm_assessment_release_metadata(uuid)",
    "ctm_reference_readable(text,jsonb)", "ctm_reference_writable(text,jsonb)",
    "ctm_staff_readable()", "ctm_staff_writable(text,jsonb)", "ctm_staff_mutable(text,jsonb)",
    "ctm_council_result_update(jsonb)", "ctm_reconsideration_readable(jsonb)",
    "ctm_reconsideration_writable(text,jsonb)", "ctm_request_readable(jsonb)",
    "ctm_request_writable(jsonb,text)", "ctm_report_root_readable(jsonb)",
    "ctm_report_root_writable(jsonb)", "ctm_request_source_writable(text,jsonb)",
    "ctm_call_readable()", "ctm_call_writable(jsonb)", "ctm_media_readable(text,jsonb)",
    "ctm_media_writable(text,jsonb,text)", "ctm_pending_readable(jsonb)",
    "ctm_pending_writable(jsonb,text)", "ctm_media_status(uuid)",
    "ctm_supplement_manifest_valid(jsonb)", "ctm_allocate_case_number(date)",
    "ctm_message_delivery_valid(uuid,uuid)", "ctm_draft_warning_current(uuid,timestamptz,uuid)",
]


def grant():
    """No production runtime-grant script exists in the repository yet (status.md: unfinished).

    This applies the same table grants the backend's own runtime-role tests apply, and only
    reports - never adds - function EXECUTE grants, so missing migration grants stay visible.
    """
    with superuser(DB) as conn:
        conn.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO ctm_app")
        conn.execute("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO ctm_app")
        role = conn.execute(
            "SELECT rolsuper, rolbypassrls, rolinherit FROM pg_roles WHERE rolname='ctm_app'").fetchone()
        missing = []
        for signature in FIXTURE_FUNCTIONS:
            try:
                ok = conn.execute("SELECT has_function_privilege('ctm_app', %s, 'EXECUTE')",
                                  ["public." + signature]).fetchone()[0]
            except psycopg.Error:
                ok = None
            if not ok:
                missing.append(signature)
        forced = conn.execute(
            "SELECT count(*) FILTER (WHERE relforcerowsecurity), count(*) FROM pg_class c "
            "JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND c.relkind='r' "
            "AND c.relname LIKE 'tribunal\\_%'").fetchone()
        report_tables = conn.execute(
            "SELECT relname, relrowsecurity, relforcerowsecurity FROM pg_class WHERE relname IN "
            "('tribunal_report','tribunal_reportrevision','tribunal_reportrequest') ORDER BY relname").fetchall()
    result = {
        "runtime_role": "ctm_app",
        "rolsuper": role[0], "rolbypassrls": role[1], "rolinherit": role[2],
        "tribunal_tables_forced_rls": forced[0], "tribunal_tables_total": forced[1],
        "report_tables_rls": [{"table": t, "rls": r, "forced": f} for t, r, f in report_tables],
        "fixture_functions_missing_execute_for_ctm_app": missing,
    }
    out = EVIDENCE / "database-roles.json"
    out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    {"create": create, "grant": grant}[sys.argv[1]]()
