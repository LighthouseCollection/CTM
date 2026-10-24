from pathlib import Path
from django.db import migrations


MODELS = ["DecisionRevision", "Vote", "PresidentialApproval", "SignatureAttestation", "Decree", "DecreeRelease"]
ENTRYPOINTS = ["ctm_decision_readable(text,jsonb)", "ctm_decision_writable(text,jsonb)", "ctm_decree_writable(jsonb)"]
FUNCTIONS = ENTRYPOINTS + ["ctm_safe_council_pdf(uuid,uuid)"]


def install(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute(Path(__file__).with_suffix(".sql").read_text())
    quote = schema_editor.quote_name
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("SELECT current_user")
        owner = cursor.fetchone()[0]
        cursor.execute("SELECT rolname FROM pg_roles WHERE rolname IN ('ctm_app','ctm_worker')")
        roles = [row[0] for row in cursor.fetchall()]
    for function in FUNCTIONS:
        schema_editor.execute(f"REVOKE ALL ON FUNCTION public.{function} FROM PUBLIC")
    for role in roles:
        for function in ENTRYPOINTS:
            schema_editor.execute(f"GRANT EXECUTE ON FUNCTION public.{function} TO {quote(role)}")
    for name in MODELS:
        table = quote(apps.get_model("tribunal", name)._meta.db_table)
        resource = name.lower()
        schema_editor.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        schema_editor.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        schema_editor.execute(f"CREATE POLICY migration_owner ON {table} TO {quote(owner)} USING (true) WITH CHECK (true)")
        schema_editor.execute(f"CREATE POLICY decision_select ON {table} FOR SELECT USING (public.ctm_decision_readable('{resource}',to_jsonb({table})))")
        check = f"public.ctm_decree_writable(to_jsonb({table}))" if name == "Decree" else f"public.ctm_decision_writable('{resource}',to_jsonb({table}))"
        schema_editor.execute(f"CREATE POLICY decision_insert ON {table} FOR INSERT WITH CHECK ({check})")


def uninstall(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    for name in MODELS:
        table = schema_editor.quote_name(apps.get_model("tribunal", name)._meta.db_table)
        for policy in ["migration_owner", "decision_select", "decision_insert"]:
            schema_editor.execute(f"DROP POLICY IF EXISTS {policy} ON {table}")
        schema_editor.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
        schema_editor.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
    for function in FUNCTIONS:
        schema_editor.execute(f"DROP FUNCTION IF EXISTS public.{function}")


class Migration(migrations.Migration):
    dependencies = [("tribunal", "0012_council_privacy")]
    operations = [migrations.RunPython(install, uninstall)]
