"""Council session emails in the Outbox and the worker's delivery check (#116, D-0036)."""
from pathlib import Path
from django.db import migrations

POLICY_FUNCTIONS = ["ctm_session_notice_allowed(jsonb)", "ctm_session_reminder_readable(jsonb)"]
WORKER_FUNCTIONS = ["ctm_session_delivery_current(uuid)"]


def grant_runtime(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("SELECT rolname FROM pg_roles WHERE rolname IN ('ctm_app','ctm_worker')")
        roles = [row[0] for row in cursor.fetchall()]
        for role in roles:
            # Every Outbox query by either role evaluates both new policies.
            for signature in POLICY_FUNCTIONS:
                cursor.execute(f"GRANT EXECUTE ON FUNCTION public.{signature} TO {role}")
            if role == "ctm_worker":
                for signature in WORKER_FUNCTIONS:
                    cursor.execute(f"GRANT EXECUTE ON FUNCTION public.{signature} TO {role}")


def install(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute(Path(__file__).with_suffix(".sql").read_text())
    for signature in POLICY_FUNCTIONS + WORKER_FUNCTIONS:
        schema_editor.execute(f"REVOKE ALL ON FUNCTION public.{signature} FROM PUBLIC")
    schema_editor.execute("CREATE POLICY session_notice_insert ON public.tribunal_outbox FOR INSERT "
                          "WITH CHECK (public.ctm_session_notice_allowed(to_jsonb(tribunal_outbox)))")
    schema_editor.execute("CREATE POLICY session_reminder_select ON public.tribunal_outbox FOR SELECT "
                          "USING (public.ctm_session_reminder_readable(to_jsonb(tribunal_outbox)))")
    grant_runtime(apps, schema_editor)


def uninstall(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute("DROP POLICY session_reminder_select ON public.tribunal_outbox")
    schema_editor.execute("DROP POLICY session_notice_insert ON public.tribunal_outbox")
    for signature in POLICY_FUNCTIONS + WORKER_FUNCTIONS:
        schema_editor.execute(f"DROP FUNCTION public.{signature}")


class Migration(migrations.Migration):
    dependencies = [("tribunal", "0069_session_response_guards")]
    operations = [migrations.RunPython(install, uninstall)]
