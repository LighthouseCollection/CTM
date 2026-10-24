from pathlib import Path
from django.db import migrations

MODELS = ["Recording", "ProcessingRun", "TranscriptRevision", "TranscriptReview"]
ENTRYPOINTS = ["ctm_media_readable(text,jsonb)", "ctm_media_writable(text,jsonb,text)"]
FUNCTIONS = ENTRYPOINTS + ["ctm_media_recording_visible(uuid)", "ctm_media_reviewer(uuid)",
    "ctm_media_safe(uuid)", "ctm_guard_media_history()"]


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
    for signature in FUNCTIONS:
        schema_editor.execute(f"REVOKE ALL ON FUNCTION public.{signature} FROM PUBLIC")
    for role in roles:
        for signature in ENTRYPOINTS:
            schema_editor.execute(f"GRANT EXECUTE ON FUNCTION public.{signature} TO {quote(role)}")
    for name in MODELS:
        table = quote(apps.get_model("tribunal", name)._meta.db_table)
        resource = name.lower()
        schema_editor.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        schema_editor.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        schema_editor.execute(f"CREATE POLICY migration_owner ON {table} TO {quote(owner)} USING (true) WITH CHECK (true)")
        schema_editor.execute(f"CREATE POLICY media_select ON {table} FOR SELECT USING (public.ctm_media_readable('{resource}',to_jsonb({table})))")
        schema_editor.execute(f"CREATE POLICY media_insert ON {table} FOR INSERT WITH CHECK (public.ctm_media_writable('{resource}',to_jsonb({table}),'insert'))")
        if name == "Recording":
            schema_editor.execute(f"CREATE POLICY media_update ON {table} FOR UPDATE USING (public.ctm_media_writable('{resource}',to_jsonb({table}),'lock')) WITH CHECK (public.ctm_media_writable('{resource}',to_jsonb({table}),'update'))")
        schema_editor.execute(f"CREATE TRIGGER retained_media_delete BEFORE DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION public.ctm_reject_history_update()")
    for table in ["tribunal_processingrun", "tribunal_transcriptrevision", "tribunal_transcriptreview"]:
        schema_editor.execute(f"CREATE TRIGGER media_provenance BEFORE INSERT OR UPDATE ON {table} FOR EACH ROW EXECUTE FUNCTION public.ctm_guard_media_history()")


def uninstall(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    for table in ["tribunal_processingrun", "tribunal_transcriptrevision", "tribunal_transcriptreview"]:
        schema_editor.execute(f"DROP TRIGGER media_provenance ON {table}")
    for name in MODELS:
        table = schema_editor.quote_name(apps.get_model("tribunal", name)._meta.db_table)
        schema_editor.execute(f"DROP TRIGGER retained_media_delete ON {table}")
        for policy in ["migration_owner", "media_select", "media_insert"] + (["media_update"] if name == "Recording" else []):
            schema_editor.execute(f"DROP POLICY {policy} ON {table}")
        schema_editor.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
        schema_editor.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
    for signature in FUNCTIONS:
        schema_editor.execute(f"DROP FUNCTION public.{signature}")


class Migration(migrations.Migration):
    dependencies = [("tribunal", "0026_remove_processingrun_file_processing_identity_and_more")]
    operations = [migrations.RunPython(install, uninstall)]
