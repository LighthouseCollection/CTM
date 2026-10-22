from django.db import migrations

SQL = """
CREATE FUNCTION public.ctm_orphan_cleanup_allowed(target text) RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public AS $$
BEGIN
 PERFORM pg_advisory_xact_lock(hashtextextended('storage:'||target,0));
 RETURN NOT EXISTS(SELECT 1 FROM public.tribunal_fileversion WHERE object_key=target);
END $$;
REVOKE ALL ON FUNCTION public.ctm_orphan_cleanup_allowed(text) FROM PUBLIC;

CREATE FUNCTION public.ctm_queue_source_guard() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog,public AS $$
BEGIN
 IF TG_TABLE_NAME='tribunal_fileversion' THEN
  PERFORM pg_advisory_xact_lock(hashtextextended('storage:'||NEW.object_key,0));
  RETURN NEW;
 END IF;
 IF (NEW.id,NEW.key,NEW.kind,NEW.case_id,NEW.recipient_id,NEW.created_at) IS DISTINCT FROM
    (OLD.id,OLD.key,OLD.kind,OLD.case_id,OLD.recipient_id,OLD.created_at) THEN
  RAISE EXCEPTION 'Queue source identity is retained' USING ERRCODE='42501';
 END IF;
 IF NEW.payload IS DISTINCT FROM OLD.payload AND NOT (
    OLD.kind='message_session' AND OLD.delivered_at IS NULL AND OLD.discarded_at IS NULL
    AND NEW.payload-'session'=OLD.payload-'session'
    AND EXISTS(SELECT 1 FROM public.tribunal_message m
      JOIN public.tribunal_councilsession s ON s.id=m.session_id
      WHERE m.id::text=OLD.payload->>'message' AND m.session_id::text=NEW.payload->>'session' AND s.state='planned')) THEN
  RAISE EXCEPTION 'Queue payload is retained except explicit session transfer' USING ERRCODE='42501';
 END IF;
 RETURN NEW;
END $$;
REVOKE ALL ON FUNCTION public.ctm_queue_source_guard() FROM PUBLIC;
CREATE TRIGGER queue_source_guard BEFORE UPDATE ON tribunal_outbox
 FOR EACH ROW EXECUTE FUNCTION public.ctm_queue_source_guard();
CREATE TRIGGER file_storage_lock BEFORE INSERT ON tribunal_fileversion
 FOR EACH ROW EXECUTE FUNCTION public.ctm_queue_source_guard();
"""


def install(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute(SQL)
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("SELECT rolname FROM pg_roles WHERE rolname='ctm_worker'")
        roles = cursor.fetchall()
    for (role,) in roles:
        schema_editor.execute(f"GRANT EXECUTE ON FUNCTION public.ctm_orphan_cleanup_allowed(text) TO {schema_editor.quote_name(role)}")


def uninstall(apps, schema_editor):
    if schema_editor.connection.vendor == "postgresql":
        schema_editor.execute("DROP TRIGGER queue_source_guard ON tribunal_outbox")
        schema_editor.execute("DROP TRIGGER file_storage_lock ON tribunal_fileversion")
        schema_editor.execute("DROP FUNCTION public.ctm_queue_source_guard()")
        schema_editor.execute("DROP FUNCTION public.ctm_orphan_cleanup_allowed(text)")


class Migration(migrations.Migration):
    dependencies = [("tribunal", "0034_workspace_provenance")]
    operations = [migrations.RunPython(install, uninstall)]
