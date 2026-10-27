"""Narrow database path for a council account's first Microsoft sign-in binding.

ctm_core_guard refuses identity changes through the runtime role. The first
sign-in for an administrator-enrolled council email must still record its
Microsoft subject once. ctm_bind_microsoft_subject is the only path: it checks
every condition itself and leaves a same-transaction grant row that ctm_app
cannot write, which the guard requires before it accepts the change.
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
            cursor.execute("GRANT EXECUTE ON FUNCTION public.ctm_bind_microsoft_subject(uuid) TO ctm_app")


def install(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute((ROOT / "0065_microsoft_first_binding.sql").read_text())
    grant_runtime(apps, schema_editor)


def uninstall(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    source = (ROOT / "0050_member_administration.sql").read_text()
    guard = re.search(r"CREATE OR REPLACE FUNCTION public.ctm_core_guard\(\).*?\nEND \$\$;", source, re.S).group()
    schema_editor.execute(guard)
    schema_editor.execute("DROP FUNCTION public.ctm_bind_microsoft_subject(uuid)")
    schema_editor.execute("DROP TABLE public.ctm_microsoft_binding_grant")


class Migration(migrations.Migration):
    dependencies = [("tribunal", "0064_repair_purge_and_session_delete_guards")]
    operations = [migrations.RunPython(install, uninstall)]
