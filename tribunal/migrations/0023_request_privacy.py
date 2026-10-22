from pathlib import Path
from django.db import migrations

MODELS = ["ReportRequest", "Report"]
ENTRYPOINTS = ["ctm_request_readable(jsonb)", "ctm_request_writable(jsonb,text)",
               "ctm_report_root_readable(jsonb)", "ctm_report_root_writable(jsonb)",
               "ctm_request_source_writable(text,jsonb)"]


def install(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute(Path(__file__).with_suffix(".sql").read_text())
    quote = schema_editor.quote_name
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("SELECT current_user")
        owner = cursor.fetchone()[0]
        cursor.execute("SELECT rolname FROM pg_roles WHERE rolname IN ('ctm_app','ctm_worker')")
        roles = [r[0] for r in cursor.fetchall()]
    for signature in ENTRYPOINTS + ["ctm_guard_sent_request()"]:
        schema_editor.execute(f"REVOKE ALL ON FUNCTION public.{signature} FROM PUBLIC")
    for role in roles:
        for signature in ENTRYPOINTS:
            schema_editor.execute(f"GRANT EXECUTE ON FUNCTION public.{signature} TO {quote(role)}")
    for name in MODELS:
        table = quote(apps.get_model("tribunal", name)._meta.db_table)
        read = "ctm_request_readable" if name == "ReportRequest" else "ctm_report_root_readable"
        write = "ctm_request_writable" if name == "ReportRequest" else "ctm_report_root_writable"
        schema_editor.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        schema_editor.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        schema_editor.execute(f"CREATE POLICY migration_owner ON {table} TO {quote(owner)} USING (true) WITH CHECK (true)")
        schema_editor.execute(f"CREATE POLICY request_select ON {table} FOR SELECT USING (public.{read}(to_jsonb({table})))")
        if name == "ReportRequest":
            schema_editor.execute(f"CREATE POLICY request_insert ON {table} FOR INSERT WITH CHECK (public.{write}(to_jsonb({table}),'insert'))")
            schema_editor.execute(f"CREATE POLICY request_update ON {table} FOR UPDATE USING (public.{write}(to_jsonb({table}),'lock')) WITH CHECK (public.{write}(to_jsonb({table}),'update'))")
        else:
            schema_editor.execute(f"CREATE POLICY request_insert ON {table} FOR INSERT WITH CHECK (public.{write}(to_jsonb({table})))")
            schema_editor.execute(f"CREATE POLICY request_update ON {table} FOR UPDATE USING (public.{write}(to_jsonb({table}))) WITH CHECK (public.{write}(to_jsonb({table})))")
        schema_editor.execute(f"CREATE TRIGGER request_history_delete BEFORE DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION public.ctm_reject_history_update()")
        schema_editor.execute(f"CREATE TRIGGER sent_request_provenance BEFORE UPDATE ON {table} FOR EACH ROW EXECUTE FUNCTION public.ctm_guard_sent_request()")
    owner_literal = "'" + owner.replace("'", "''") + "'"
    for resource in ["medicalrelease", "reportrevision", "attachment", "fileversion"]:
        table = quote("tribunal_" + resource)
        schema_editor.execute(f"CREATE POLICY request_source_insert ON {table} AS RESTRICTIVE FOR INSERT WITH CHECK (current_user={owner_literal} OR public.ctm_request_source_writable('{resource}',to_jsonb({table})))")
    schema_editor.execute("CREATE TRIGGER request_attachment_scope BEFORE UPDATE ON tribunal_attachment FOR EACH ROW EXECUTE FUNCTION public.ctm_guard_sent_request()")


def uninstall(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute("DROP TRIGGER request_attachment_scope ON tribunal_attachment")
    for resource in ["medicalrelease", "reportrevision", "attachment", "fileversion"]:
        schema_editor.execute(f"DROP POLICY request_source_insert ON tribunal_{resource}")
    for name in MODELS:
        table = schema_editor.quote_name(apps.get_model("tribunal", name)._meta.db_table)
        for trigger in ["request_history_delete", "sent_request_provenance"]:
            schema_editor.execute(f"DROP TRIGGER {trigger} ON {table}")
        for policy in ["migration_owner", "request_select", "request_insert", "request_update"]:
            schema_editor.execute(f"DROP POLICY {policy} ON {table}")
        schema_editor.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
        schema_editor.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
    for signature in ENTRYPOINTS + ["ctm_guard_sent_request()"]:
        schema_editor.execute(f"DROP FUNCTION public.{signature}")


class Migration(migrations.Migration):
    dependencies = [("tribunal", "0022_application_origin_and_more")]
    operations = [migrations.RunPython(install, uninstall)]
