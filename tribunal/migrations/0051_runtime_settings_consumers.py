"""Bounded read-only projections for two nonsecret runtime settings."""

from pathlib import Path

from django.db import migrations


def grant_runtime(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("SELECT 1 FROM pg_roles WHERE rolname='ctm_app'")
        if cursor.fetchone():
            cursor.execute(
                "GRANT EXECUTE ON FUNCTION "
                "public.ctm_runtime_tribunal_contact() TO ctm_app"
            )
            cursor.execute(
                "GRANT EXECUTE ON FUNCTION "
                "public.ctm_case_recommended_doctors(uuid,text) TO ctm_app"
            )


def install(apps, schema_editor):
    if schema_editor.connection.vendor == "postgresql":
        schema_editor.execute(Path(__file__).with_suffix(".sql").read_text())
        grant_runtime(apps, schema_editor)


def uninstall(apps, schema_editor):
    if schema_editor.connection.vendor == "postgresql":
        schema_editor.execute(
            "DROP FUNCTION public.ctm_case_recommended_doctors(uuid,text)"
        )
        schema_editor.execute(
            "DROP FUNCTION public.ctm_runtime_tribunal_contact()"
        )


class Migration(migrations.Migration):
    dependencies = [("tribunal", "0050_member_administration")]
    operations = [migrations.RunPython(install, uninstall)]
