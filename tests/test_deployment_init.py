"""Fresh deployment SQL exercised only inside the disposable GitHub PG service."""

import os
import shutil
import subprocess
from pathlib import Path
import pytest
from django.db import connection

pytestmark = pytest.mark.django_db(transaction=True)


def test_fresh_role_initialization_handles_literal_passwords_and_is_idempotent():
    if connection.vendor != "postgresql" or os.environ.get("GITHUB_ACTIONS") != "true":
        pytest.skip("Disposable GitHub PostgreSQL service only")
    config = connection.settings_dict
    if (
        not config["NAME"].startswith("test_")
        or not shutil.which("psql")
        or not shutil.which("bash")
    ):
        pytest.skip("Requires isolated test database and psql/bash")
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT rolname FROM pg_roles WHERE rolname IN ('ctm_app','ctm_worker')"
        )
        if cursor.fetchall():
            pytest.skip("Never change preexisting deployment roles")
    root = Path(__file__).resolve().parents[1]
    password = "synthetic'$$;\\literal\nend"
    worker_password = "worker'$$\\end"
    env = dict(
        os.environ,
        PGHOST=config["HOST"],
        PGPORT=str(config["PORT"]),
        POSTGRES_USER=config["USER"],
        POSTGRES_DB=config["NAME"],
        POSTGRES_PASSWORD=config["PASSWORD"],
        CTM_APP_PASSWORD=password,
        CTM_WORKER_PASSWORD=worker_password,
        CTM_INIT_SQL=str(root / "deploy/postgres/init.sql"),
    )

    def initialize():
        result = subprocess.run(
            ["bash", str(root / "deploy/postgres/00-init-roles.sh")],
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, (
            "Fresh role initialization failed; secret-bearing SQL diagnostics withheld"
        )

    try:
        initialize()
        env["CTM_APP_PASSWORD"] = "new-value-must-not-reset-existing-password"
        initialize()
        import psycopg

        with psycopg.connect(
            host=config["HOST"],
            port=config["PORT"],
            dbname=config["NAME"],
            user="ctm_app",
            password=password,
        ) as runtime:
            row = runtime.execute(
                "SELECT rolsuper,rolbypassrls,rolcreatedb,rolcreaterole,rolreplication,rolinherit FROM pg_roles WHERE rolname=current_user"
            ).fetchone()
            assert not any(row)
            assert runtime.execute(
                "SELECT has_table_privilege(current_user,'tribunal_account','SELECT')"
            ).fetchone() == (False,)
    finally:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT rolname FROM pg_roles WHERE rolname IN ('ctm_app','ctm_worker')"
            )
            roles = {row[0] for row in cursor.fetchall()}
            for role in ["ctm_app", "ctm_worker"]:
                if role in roles:
                    # These roles did not exist before this isolated test.
                    cursor.execute(f"DROP OWNED BY {role}")
                    cursor.execute(f"DROP ROLE {role}")
