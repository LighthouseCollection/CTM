from pathlib import Path
import re
from django.db import migrations

ENTRYPOINTS = ["ctm_call_readable()", "ctm_call_writable(jsonb)"]
FUNCTIONS = ENTRYPOINTS + ["ctm_guard_checkout_link()", "ctm_guard_recording_scope()"]
MEDICAL_HELPERS = ["ctm_attachment_visible", "ctm_report_visible", "ctm_source_readable"]


def medical_helper(name):
    source = Path(__file__).with_name("0011_source_privacy.sql").read_text()
    return re.search(r"CREATE FUNCTION public\." + name + r"\(.*?\$\$;", source, re.S).group().replace("CREATE FUNCTION", "CREATE OR REPLACE FUNCTION", 1)


def install(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute(Path(__file__).with_suffix(".sql").read_text())
    for name in MEDICAL_HELPERS:
        sql = medical_helper(name)
        sql = sql.replace("r.scope->>'council'='true'", "r.scope->'council'='true'::jsonb")
        sql = sql.replace("release.scope->>'council'='true'", "release.scope->'council'='true'::jsonb")
        sql = sql.replace("data->'scope'->>'council'='true'", "data->'scope'->'council'='true'::jsonb")
        if name == "ctm_report_visible":
            sql = sql.replace("(p.author_id=", "(r.sent_at IS NOT NULL AND p.author_id=")
        schema_editor.execute(sql)
    quote = schema_editor.quote_name
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("SELECT current_user")
        owner = cursor.fetchone()[0]
        cursor.execute("SELECT rolname FROM pg_roles WHERE rolname IN ('ctm_app','ctm_worker')")
        roles = [row[0] for row in cursor.fetchall()]
    for signature in FUNCTIONS:
        schema_editor.execute(f"REVOKE ALL ON FUNCTION public.{signature} FROM PUBLIC")
    for role in roles:
        for signature in ENTRYPOINTS:
            schema_editor.execute(f"GRANT EXECUTE ON FUNCTION public.{signature} TO {quote(role)}")
    table = "tribunal_callrecord"
    schema_editor.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
    schema_editor.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
    schema_editor.execute(f"CREATE POLICY migration_owner ON {table} TO {quote(owner)} USING (true) WITH CHECK (true)")
    schema_editor.execute(f"CREATE POLICY call_select ON {table} FOR SELECT USING (public.ctm_call_readable())")
    schema_editor.execute(f"CREATE POLICY call_insert ON {table} FOR INSERT WITH CHECK (public.ctm_call_writable(to_jsonb({table})))")
    for op in ["UPDATE", "DELETE"]:
        schema_editor.execute(f"CREATE TRIGGER retained_call_{op.lower()} BEFORE {op} ON {table} FOR EACH ROW EXECUTE FUNCTION public.ctm_reject_history_update()")


def uninstall(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    for name in MEDICAL_HELPERS:
        schema_editor.execute(medical_helper(name))
    schema_editor.execute("DROP TRIGGER checkout_link_provenance ON tribunal_checkoutintent")
    schema_editor.execute("DROP TRIGGER recording_source_scope ON tribunal_recording")
    for op in ["update", "delete"]:
        schema_editor.execute(f"DROP TRIGGER retained_call_{op} ON tribunal_callrecord")
    for policy in ["migration_owner", "call_select", "call_insert"]:
        schema_editor.execute(f"DROP POLICY {policy} ON tribunal_callrecord")
    schema_editor.execute("ALTER TABLE tribunal_callrecord NO FORCE ROW LEVEL SECURITY")
    schema_editor.execute("ALTER TABLE tribunal_callrecord DISABLE ROW LEVEL SECURITY")
    for signature in FUNCTIONS:
        schema_editor.execute(f"DROP FUNCTION public.{signature}")


class Migration(migrations.Migration):
    dependencies = [("tribunal", "0024_checkoutintent_checkout_expires_at_and_more")]
    operations = [migrations.RunPython(install, uninstall)]
