"""Row security, append-only and clock guards for SessionResponse, and a rising
.ics sequence on CouncilSession (#116, D-0036)."""
from pathlib import Path
from django.db import migrations

TABLE = "tribunal_sessionresponse"
ENTRYPOINTS = ["ctm_session_response_readable(jsonb)", "ctm_session_response_writable(jsonb)"]
FUNCTIONS = ENTRYPOINTS + ["ctm_session_response_stamp()", "ctm_session_ics_sequence_rises()"]


def grant_runtime(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("SELECT 1 FROM pg_roles WHERE rolname='ctm_app'")
        if cursor.fetchone():
            # Append-only: no UPDATE or DELETE for the runtime role.
            cursor.execute(f"GRANT SELECT, INSERT ON TABLE public.{TABLE} TO ctm_app")
            for signature in ENTRYPOINTS:
                cursor.execute(f"GRANT EXECUTE ON FUNCTION public.{signature} TO ctm_app")


def install(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute(Path(__file__).with_suffix(".sql").read_text())
    quote = schema_editor.quote_name
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("SELECT current_user")
        owner = cursor.fetchone()[0]
    for signature in FUNCTIONS:
        schema_editor.execute(f"REVOKE ALL ON FUNCTION public.{signature} FROM PUBLIC")
    schema_editor.execute(f"REVOKE ALL ON TABLE {TABLE} FROM PUBLIC")
    schema_editor.execute(f"ALTER TABLE {TABLE} ENABLE ROW LEVEL SECURITY")
    schema_editor.execute(f"ALTER TABLE {TABLE} FORCE ROW LEVEL SECURITY")
    schema_editor.execute(f"CREATE POLICY migration_owner ON {TABLE} TO {quote(owner)} USING (true) WITH CHECK (true)")
    schema_editor.execute(f"CREATE POLICY response_select ON {TABLE} FOR SELECT USING (public.ctm_session_response_readable(to_jsonb({TABLE})))")
    schema_editor.execute(f"CREATE POLICY response_insert ON {TABLE} FOR INSERT WITH CHECK (public.ctm_session_response_writable(to_jsonb({TABLE})))")
    schema_editor.execute(f"CREATE TRIGGER response_stamp BEFORE INSERT ON {TABLE} FOR EACH ROW EXECUTE FUNCTION public.ctm_session_response_stamp()")
    # Same history guard as the other append-only tables: refused except during an authorized admin purge.
    schema_editor.execute(f"CREATE TRIGGER response_history BEFORE UPDATE OR DELETE ON {TABLE} FOR EACH ROW EXECUTE FUNCTION public.ctm_reject_history_update()")
    schema_editor.execute("CREATE TRIGGER ics_sequence_rises BEFORE UPDATE OF ics_sequence ON tribunal_councilsession "
                          "FOR EACH ROW EXECUTE FUNCTION public.ctm_session_ics_sequence_rises()")
    grant_runtime(apps, schema_editor)


def uninstall(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute("DROP TRIGGER ics_sequence_rises ON tribunal_councilsession")
    for trigger in ["response_stamp", "response_history"]:
        schema_editor.execute(f"DROP TRIGGER {trigger} ON {TABLE}")
    for policy in ["migration_owner", "response_select", "response_insert"]:
        schema_editor.execute(f"DROP POLICY {policy} ON {TABLE}")
    schema_editor.execute(f"ALTER TABLE {TABLE} NO FORCE ROW LEVEL SECURITY")
    schema_editor.execute(f"ALTER TABLE {TABLE} DISABLE ROW LEVEL SECURITY")
    for signature in FUNCTIONS:
        schema_editor.execute(f"DROP FUNCTION public.{signature}")


class Migration(migrations.Migration):
    dependencies = [("tribunal", "0068_session_response")]
    operations = [migrations.RunPython(install, uninstall)]
