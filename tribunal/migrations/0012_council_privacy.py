from pathlib import Path
from django.db import migrations

MODELS = [
    "CouncilSession",
    "AgendaItem",
    "Attendance",
    "Hearing",
    "HearingOutcome",
    "CaseAssignment",
    "CaseNote",
    "NoteRevision",
    "FindingRevision",
]
ENTRYPOINTS = [
    "ctm_council_visible()",
    "ctm_council_writable(text,jsonb,text)",
    "ctm_council_mutable(text,jsonb)",
]
FUNCTIONS = [
    "ctm_council_mutable(text,jsonb)",
    "ctm_council_writable(text,jsonb,text)",
    "ctm_council_hearing_writer(uuid)",
    "ctm_council_proceeding_writer(uuid)",
    "ctm_council_case_writer(uuid)",
    "ctm_council_visible()",
    "ctm_preserve_council_context()",
]


def install(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute(
        Path(__file__).with_suffix(".sql").read_text(encoding="utf-8")
    )
    quote = schema_editor.quote_name
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("SELECT current_user")
        owner = cursor.fetchone()[0]
        cursor.execute(
            "SELECT rolname FROM pg_roles WHERE rolname IN ('ctm_app','ctm_worker')"
        )
        roles = [row[0] for row in cursor.fetchall()]
    for function in FUNCTIONS:
        schema_editor.execute(f"REVOKE ALL ON FUNCTION public.{function} FROM PUBLIC")
    for role in roles:
        for function in ENTRYPOINTS:
            schema_editor.execute(
                f"GRANT EXECUTE ON FUNCTION public.{function} TO {quote(role)}"
            )
    for name in MODELS:
        table = quote(apps.get_model("tribunal", name)._meta.db_table)
        resource = name.lower()
        schema_editor.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        schema_editor.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        schema_editor.execute(
            f"CREATE POLICY migration_owner ON {table} TO {quote(owner)} USING (true) WITH CHECK (true)"
        )
        schema_editor.execute(
            f"CREATE POLICY council_select ON {table} FOR SELECT USING (public.ctm_council_visible())"
        )
        schema_editor.execute(
            f"CREATE POLICY council_insert ON {table} FOR INSERT WITH CHECK (public.ctm_council_writable('{resource}',to_jsonb({table}),'insert'))"
        )
        if name in {"CouncilSession", "AgendaItem"}:
            schema_editor.execute(
                f"CREATE POLICY council_update ON {table} FOR UPDATE USING (public.ctm_council_mutable('{resource}',to_jsonb({table}))) WITH CHECK (public.ctm_council_writable('{resource}',to_jsonb({table}),'update'))"
            )


def uninstall(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    for table in ["tribunal_agendaitem", "tribunal_councilsession"]:
        schema_editor.execute(
            f"DROP TRIGGER IF EXISTS preserve_council_context ON {table}"
        )
    for name in MODELS:
        table = schema_editor.quote_name(
            apps.get_model("tribunal", name)._meta.db_table
        )
        for policy in [
            "migration_owner",
            "council_select",
            "council_insert",
            "council_update",
        ]:
            schema_editor.execute(f"DROP POLICY IF EXISTS {policy} ON {table}")
        schema_editor.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
        schema_editor.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
    for function in FUNCTIONS:
        schema_editor.execute(f"DROP FUNCTION IF EXISTS public.{function}")


class Migration(migrations.Migration):
    dependencies = [("tribunal", "0011_source_privacy")]
    operations = [migrations.RunPython(install, uninstall)]
