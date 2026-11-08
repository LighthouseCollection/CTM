"""Audited unassign of a case manager (#237, D-0056)."""
from pathlib import Path
from django.db import migrations

FUNCTION = "ctm_case_unassign_allowed(jsonb,text)"


def grant_runtime(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("SELECT rolname FROM pg_roles WHERE rolname IN ('ctm_app','ctm_worker')")
        for (role,) in cursor.fetchall():
            # Every case update by either role evaluates this policy.
            cursor.execute(f"GRANT EXECUTE ON FUNCTION public.{FUNCTION} TO {role}")


def install(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute(Path(__file__).with_suffix(".sql").read_text())
    schema_editor.execute(f"REVOKE ALL ON FUNCTION public.{FUNCTION} FROM PUBLIC")
    schema_editor.execute("CREATE POLICY case_unassign ON public.tribunal_case FOR UPDATE "
                          "USING (public.ctm_case_unassign_allowed(to_jsonb(tribunal_case),'old')) "
                          "WITH CHECK (public.ctm_case_unassign_allowed(to_jsonb(tribunal_case),'new'))")
    grant_runtime(apps, schema_editor)


def uninstall(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute("DROP POLICY case_unassign ON public.tribunal_case")
    schema_editor.execute(f"DROP FUNCTION public.{FUNCTION}")


class Migration(migrations.Migration):
    dependencies = [("tribunal", "0075_president_session_notices")]
    operations = [migrations.RunPython(install, uninstall)]
