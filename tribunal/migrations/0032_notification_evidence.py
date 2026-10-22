from django.db import migrations


SQL = """
CREATE FUNCTION public.ctm_guard_notification_evidence() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog,public AS $$
DECLARE owner_name text;
BEGIN
 IF (to_jsonb(NEW)-'read_at') IS DISTINCT FROM (to_jsonb(OLD)-'read_at')
   OR (OLD.read_at IS NOT NULL AND NEW.read_at IS DISTINCT FROM OLD.read_at) THEN
  RAISE EXCEPTION 'Notification source and first read evidence are retained' USING ERRCODE='42501';
 END IF;
 SELECT pg_get_userbyid(relowner) INTO owner_name FROM pg_class
  WHERE oid='public.tribunal_notification'::regclass;
 IF current_user<>owner_name AND NEW.read_at IS DISTINCT FROM OLD.read_at
    AND OLD.recipient_id::text IS DISTINCT FROM nullif(current_setting('ctm.actor_id',true),'') THEN
  RAISE EXCEPTION 'Only the intended notification recipient can acknowledge' USING ERRCODE='42501';
 END IF;
 RETURN NEW;
END $$;
REVOKE ALL ON FUNCTION public.ctm_guard_notification_evidence() FROM PUBLIC;
CREATE TRIGGER retained_notification_evidence BEFORE UPDATE ON tribunal_notification
 FOR EACH ROW EXECUTE FUNCTION public.ctm_guard_notification_evidence();
CREATE TRIGGER retained_notification_delete BEFORE DELETE ON tribunal_notification
 FOR EACH ROW EXECUTE FUNCTION public.ctm_reject_history_update();
"""


def install(apps, schema_editor):
    if schema_editor.connection.vendor == "postgresql":
        schema_editor.execute(SQL)


def uninstall(apps, schema_editor):
    if schema_editor.connection.vendor == "postgresql":
        schema_editor.execute("DROP TRIGGER retained_notification_evidence ON tribunal_notification")
        schema_editor.execute("DROP TRIGGER retained_notification_delete ON tribunal_notification")
        schema_editor.execute("DROP FUNCTION public.ctm_guard_notification_evidence()")


class Migration(migrations.Migration):
    dependencies = [("tribunal", "0031_delivery_and_numbering_guards")]
    operations = [migrations.RunPython(install, uninstall)]
