from pathlib import Path
from django.db import migrations

MODELS = ["Account", "Person", "Case", "Party", "Proceeding", "OpenCaseClaim", "Outbox"]
FUNCTIONS = ["ctm_context_uuid(text)", "ctm_caller()", "ctm_worker_caller()", "ctm_migration_caller()",
    "ctm_filing_application()", "ctm_filing_case(uuid)", "ctm_close_allowed(uuid)", "ctm_case_linked(uuid)",
    "ctm_historical_context()", "ctm_notice_queue_allowed(jsonb)", "ctm_core_read(text,jsonb)", "ctm_core_write(text,jsonb,text)",
    "ctm_core_guard()", "ctm_applicant_parties(uuid)", "ctm_delivery_destination(uuid)", "ctm_delay_digest(uuid,timestamptz)"]
APP_ENTRYPOINTS = ["ctm_core_read(text,jsonb)", "ctm_core_write(text,jsonb,text)", "ctm_applicant_parties(uuid)", "ctm_delay_digest(uuid,timestamptz)"]
WORKER_ENTRYPOINTS = ["ctm_core_read(text,jsonb)", "ctm_core_write(text,jsonb,text)", "ctm_delivery_destination(uuid)"]


def install(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute(Path(__file__).with_suffix(".sql").read_text())
    q = schema_editor.quote_name
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("SELECT current_user")
        owner = cursor.fetchone()[0]
        cursor.execute("SELECT rolname FROM pg_roles WHERE rolname IN ('ctm_app','ctm_worker')")
        roles = [r[0] for r in cursor.fetchall()]
    for function in FUNCTIONS:
        schema_editor.execute(f"REVOKE ALL ON FUNCTION public.{function} FROM PUBLIC")
    for role in roles:
        for function in APP_ENTRYPOINTS if role=='ctm_app' else WORKER_ENTRYPOINTS:
            schema_editor.execute(f"GRANT EXECUTE ON FUNCTION public.{function} TO {q(role)}")
    for name in MODELS:
        table = q(apps.get_model("tribunal", name)._meta.db_table)
        resource = name.lower()
        schema_editor.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        schema_editor.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        schema_editor.execute(f"CREATE POLICY migration_owner ON {table} TO {q(owner)} USING (true) WITH CHECK (true)")
        schema_editor.execute(f"CREATE POLICY core_select ON {table} FOR SELECT USING (public.ctm_core_read('{resource}',to_jsonb({table})))")
        schema_editor.execute(f"CREATE POLICY core_insert ON {table} FOR INSERT WITH CHECK (public.ctm_core_write('{resource}',to_jsonb({table}),'insert'))")
        schema_editor.execute(f"CREATE POLICY core_update ON {table} FOR UPDATE USING (public.ctm_core_write('{resource}',to_jsonb({table}),'lock')) WITH CHECK (public.ctm_core_write('{resource}',to_jsonb({table}),'update'))")
        if name == "OpenCaseClaim":
            schema_editor.execute(f"CREATE POLICY core_delete ON {table} FOR DELETE USING (public.ctm_core_write('{resource}',to_jsonb({table}),'delete'))")
        elif name != 'Outbox':
            schema_editor.execute(f"CREATE TRIGGER core_retained_delete BEFORE DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION public.ctm_reject_history_update()")
        schema_editor.execute(f"CREATE TRIGGER core_provenance BEFORE INSERT OR UPDATE ON {table} FOR EACH ROW EXECUTE FUNCTION public.ctm_core_guard()")


def uninstall(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    for name in MODELS:
        table = schema_editor.quote_name(apps.get_model("tribunal", name)._meta.db_table)
        schema_editor.execute(f"DROP TRIGGER core_provenance ON {table}")
        if name not in {'OpenCaseClaim','Outbox'}:
            schema_editor.execute(f"DROP TRIGGER core_retained_delete ON {table}")
        for policy in ["migration_owner", "core_select", "core_insert", "core_update"] + (["core_delete"] if name=='OpenCaseClaim' else []):
            schema_editor.execute(f"DROP POLICY {policy} ON {table}")
        schema_editor.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
        schema_editor.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
    # Restore pre-core actor lookup before removing its caller dependencies.
    schema_editor.execute("""CREATE OR REPLACE FUNCTION public.ctm_actor_id() RETURNS uuid LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
    BEGIN RETURN nullif(current_setting('ctm.actor_id',true),'')::uuid; EXCEPTION WHEN invalid_text_representation THEN RETURN NULL; END $$;""")
    for function in reversed(FUNCTIONS):
        schema_editor.execute(f"DROP FUNCTION public.{function}")


class Migration(migrations.Migration):
    dependencies = [("tribunal", "0036_outbox_actor_provenance")]
    operations = [migrations.RunPython(install, uninstall)]
