from pathlib import Path
import re
from django.db import migrations

ENTRYPOINTS = ["ctm_pending_readable(jsonb)", "ctm_pending_writable(jsonb,text)",
    "ctm_media_status(uuid)", "ctm_supplement_manifest_valid(jsonb)"]
FUNCTIONS = ENTRYPOINTS + ["ctm_guard_twenty()"]


def original(name):
    source = Path(__file__).with_name("0027_media_privacy.sql").read_text()
    return re.search(r"CREATE FUNCTION public\."+name+r"\(.*?\$\$;", source, re.S).group().replace("CREATE FUNCTION", "CREATE OR REPLACE FUNCTION", 1)


def install(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute(Path(__file__).with_suffix(".sql").read_text())
    readable = original("ctm_media_readable").replace("AND public.ctm_media_recording_visible(x.id));", "AND public.ctm_media_reviewer(x.id));")
    schema_editor.execute(readable)
    writable = original("ctm_media_writable").replace("RETURN false; -- provider output", """
 IF resource='transcriptrevision' THEN
  RETURN data->>'actor_id'=public.ctm_actor_id()::text AND EXISTS(
   SELECT 1 FROM public.tribunal_transcriptrevision prior JOIN public.tribunal_processingrun run ON run.id=prior.run_id
   WHERE prior.recording_id=(data->>'recording_id')::uuid AND prior.run_id=(data->>'run_id')::uuid
    AND prior.kind=data->>'kind' AND prior.language=data->>'language' AND run.state='completed'
    AND public.ctm_media_safe(prior.recording_id) AND public.ctm_media_reviewer(prior.recording_id)
    AND (data->>'number')::int=(SELECT max(v.number)+1 FROM public.tribunal_transcriptrevision v
       WHERE v.recording_id=prior.recording_id AND v.kind=prior.kind AND v.language=prior.language));
 END IF;
 RETURN false; -- provider output""")
    schema_editor.execute(writable)
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
    table = "tribunal_pendingpartylink"
    schema_editor.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
    schema_editor.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
    schema_editor.execute(f"CREATE POLICY migration_owner ON {table} TO {quote(owner)} USING (true) WITH CHECK (true)")
    schema_editor.execute(f"CREATE POLICY pending_select ON {table} FOR SELECT USING (public.ctm_pending_readable(to_jsonb({table})))")
    schema_editor.execute(f"CREATE POLICY pending_insert ON {table} FOR INSERT WITH CHECK (public.ctm_pending_writable(to_jsonb({table}),'insert'))")
    schema_editor.execute(f"CREATE POLICY pending_update ON {table} FOR UPDATE USING (public.ctm_pending_readable(to_jsonb({table}))) WITH CHECK (public.ctm_pending_writable(to_jsonb({table}),'update'))")
    schema_editor.execute(f"CREATE TRIGGER pending_retention BEFORE DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION public.ctm_reject_history_update()")
    for table in ["tribunal_pendingpartylink", "tribunal_recording", "tribunal_historicalworkspace"]:
        schema_editor.execute(f"CREATE TRIGGER twenty_provenance BEFORE UPDATE ON {table} FOR EACH ROW EXECUTE FUNCTION public.ctm_guard_twenty()")
    owner_literal = "'"+owner.replace("'", "''")+"'"
    schema_editor.execute(f"CREATE POLICY capture_actor ON tribunal_recording AS RESTRICTIVE FOR INSERT WITH CHECK (current_user={owner_literal} OR captured_by_id::text=current_setting('ctm.actor_id',true))")
    schema_editor.execute(f"CREATE POLICY supplement_manifest ON tribunal_appealsupplement AS RESTRICTIVE FOR INSERT WITH CHECK (current_user={owner_literal} OR public.ctm_supplement_manifest_valid(to_jsonb(tribunal_appealsupplement)))")


def uninstall(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    for name in ["ctm_media_readable", "ctm_media_writable"]:
        schema_editor.execute(original(name))
    schema_editor.execute("DROP POLICY capture_actor ON tribunal_recording")
    schema_editor.execute("DROP POLICY supplement_manifest ON tribunal_appealsupplement")
    for table in ["tribunal_pendingpartylink", "tribunal_recording", "tribunal_historicalworkspace"]:
        schema_editor.execute(f"DROP TRIGGER twenty_provenance ON {table}")
    schema_editor.execute("DROP TRIGGER pending_retention ON tribunal_pendingpartylink")
    for policy in ["migration_owner", "pending_select", "pending_insert", "pending_update"]:
        schema_editor.execute(f"DROP POLICY {policy} ON tribunal_pendingpartylink")
    schema_editor.execute("ALTER TABLE tribunal_pendingpartylink NO FORCE ROW LEVEL SECURITY")
    schema_editor.execute("ALTER TABLE tribunal_pendingpartylink DISABLE ROW LEVEL SECURITY")
    for signature in FUNCTIONS:
        schema_editor.execute(f"DROP FUNCTION public.{signature}")


class Migration(migrations.Migration):
    dependencies = [("tribunal", "0028_appealsupplement_idempotency_key_and_more")]
    operations = [migrations.RunPython(install, uninstall)]
