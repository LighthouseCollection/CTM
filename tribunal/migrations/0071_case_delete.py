"""Case deletion by admin, president or secretary (#176, D-0044).

ctm_delete_case(case_id, reason) re-checks the caller's role, deletes the case
and everything that belongs only to it, and leaves one audit entry. The history
triggers open only inside that function, through a same-transaction grant row.
"""
import re
from pathlib import Path
from django.db import migrations

ROOT = Path(__file__).parent


def grant_runtime(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("SELECT 1 FROM pg_roles WHERE rolname='ctm_app'")
        if cursor.fetchone():
            cursor.execute("GRANT EXECUTE ON FUNCTION public.ctm_delete_case(uuid,text) TO ctm_app")


def install(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute((ROOT / "0071_case_delete.sql").read_text())
    grant_runtime(apps, schema_editor)


def uninstall(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    source = (ROOT / "0057_admin_case_purge.py").read_text()
    for name in ["ctm_admin_case_purge_allowed", "ctm_admin_case_purge_active", "ctm_purge_case"]:
        definition = re.search(r"CREATE OR REPLACE FUNCTION public\." + name + r"\(.*?\n(?:END )?\$\$;", source, re.S).group()
        if name == "ctm_purge_case":
            schema_editor.execute("DROP FUNCTION public.ctm_purge_case(uuid)")
            definition = definition.replace("CREATE OR REPLACE FUNCTION", "CREATE FUNCTION", 1)
        schema_editor.execute(definition)
    schema_editor.execute("REVOKE ALL ON FUNCTION public.ctm_purge_case(uuid) FROM PUBLIC")
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("SELECT 1 FROM pg_roles WHERE rolname='ctm_app'")
        if cursor.fetchone():
            cursor.execute("GRANT EXECUTE ON FUNCTION public.ctm_purge_case(uuid) TO ctm_app")
    schema_editor.execute("DROP FUNCTION public.ctm_delete_case(uuid,text)")
    schema_editor.execute("DROP TABLE public.ctm_case_delete_grant")


class Migration(migrations.Migration):
    dependencies = [("tribunal", "0070_session_notice_outbox")]
    operations = [migrations.RunPython(install, uninstall)]
