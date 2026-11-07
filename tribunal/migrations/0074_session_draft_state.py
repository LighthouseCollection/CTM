"""Council sessions move between Draft and In progress before adjournment (#224, D-0052)."""
from pathlib import Path
from django.db import migrations

TABLE = "public.tribunal_councilsession"
FUNCTIONS = ["ctm_session_draft_state_writable(jsonb)", "ctm_session_draft_insertable(jsonb)"]


def grant_runtime(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("SELECT rolname FROM pg_roles WHERE rolname IN ('ctm_app','ctm_worker')")
        for (role,) in cursor.fetchall():
            # Every session write by either role evaluates these policies.
            for signature in FUNCTIONS:
                cursor.execute(f"GRANT EXECUTE ON FUNCTION public.{signature} TO {role}")


def install(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute(Path(__file__).with_suffix(".sql").read_text())
    for signature in FUNCTIONS:
        schema_editor.execute(f"REVOKE ALL ON FUNCTION public.{signature} FROM PUBLIC")
    schema_editor.execute(f"CREATE POLICY session_draft_state ON {TABLE} FOR UPDATE "
                          "USING (public.ctm_session_draft_state_writable(to_jsonb(tribunal_councilsession))) "
                          "WITH CHECK (public.ctm_session_draft_state_writable(to_jsonb(tribunal_councilsession)))")
    schema_editor.execute(f"CREATE POLICY session_draft_insert ON {TABLE} FOR INSERT "
                          "WITH CHECK (public.ctm_session_draft_insertable(to_jsonb(tribunal_councilsession)))")
    grant_runtime(apps, schema_editor)


def uninstall(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute(f"DROP POLICY session_draft_insert ON {TABLE}")
    schema_editor.execute(f"DROP POLICY session_draft_state ON {TABLE}")
    for signature in FUNCTIONS:
        schema_editor.execute(f"DROP FUNCTION public.{signature}")


class Migration(migrations.Migration):
    dependencies = [("tribunal", "0073_council_seat_guards")]
    operations = [migrations.RunPython(install, uninstall)]
