"""Row security and the ballot rule for council seats (#175, D-0043)."""
from pathlib import Path
from django.db import migrations

TABLE = "tribunal_councilseatchange"
APP_FUNCTIONS = ["ctm_council_seat(uuid)", "ctm_voting_seat(uuid)",
                 "ctm_council_seat_readable()", "ctm_council_seat_writable(jsonb)"]
FUNCTIONS = APP_FUNCTIONS + ["ctm_council_seat_stamp()"]


def grant_runtime(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("SELECT 1 FROM pg_roles WHERE rolname='ctm_app'")
        if cursor.fetchone():
            # Append-only: no UPDATE or DELETE for the runtime role.
            cursor.execute(f"GRANT SELECT, INSERT ON TABLE public.{TABLE} TO ctm_app")
            for signature in APP_FUNCTIONS:
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
    schema_editor.execute(f"CREATE POLICY seat_select ON {TABLE} FOR SELECT USING (public.ctm_council_seat_readable())")
    schema_editor.execute(f"CREATE POLICY seat_insert ON {TABLE} FOR INSERT WITH CHECK (public.ctm_council_seat_writable(to_jsonb({TABLE})))")
    schema_editor.execute(f"CREATE TRIGGER seat_stamp BEFORE INSERT ON {TABLE} FOR EACH ROW EXECUTE FUNCTION public.ctm_council_seat_stamp()")
    schema_editor.execute(f"CREATE TRIGGER seat_history BEFORE UPDATE OR DELETE ON {TABLE} FOR EACH ROW EXECUTE FUNCTION public.ctm_reject_history_update()")
    # The ballot: a vote is recorded only for an account that holds a voting seat now.
    owner_literal = "'" + owner.replace("'", "''") + "'"
    schema_editor.execute("CREATE POLICY vote_voting_seat ON public.tribunal_vote AS RESTRICTIVE FOR INSERT "
                          f"WITH CHECK (current_user={owner_literal} OR public.ctm_voting_seat(member_id))")
    grant_runtime(apps, schema_editor)


def uninstall(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute("DROP POLICY vote_voting_seat ON public.tribunal_vote")
    for trigger in ["seat_stamp", "seat_history"]:
        schema_editor.execute(f"DROP TRIGGER {trigger} ON {TABLE}")
    for policy in ["migration_owner", "seat_select", "seat_insert"]:
        schema_editor.execute(f"DROP POLICY {policy} ON {TABLE}")
    schema_editor.execute(f"ALTER TABLE {TABLE} NO FORCE ROW LEVEL SECURITY")
    schema_editor.execute(f"ALTER TABLE {TABLE} DISABLE ROW LEVEL SECURITY")
    for signature in FUNCTIONS:
        schema_editor.execute(f"DROP FUNCTION public.{signature}")


class Migration(migrations.Migration):
    dependencies = [("tribunal", "0072_council_seat_change")]
    operations = [migrations.RunPython(install, uninstall)]
