from django.db import migrations


SQL = """
CREATE FUNCTION public.ctm_workspace_version_guard() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog,public AS $$
BEGIN
 IF TG_OP='INSERT' THEN
  IF NEW.version<>1 THEN
   RAISE EXCEPTION 'Workspace starts at version one' USING ERRCODE='23514';
  END IF;
  RETURN NEW;
 END IF;
 IF (NEW.id,NEW.actor_id,NEW.created_at) IS DISTINCT FROM (OLD.id,OLD.actor_id,OLD.created_at)
    OR (OLD.finalized_case_id IS NOT NULL AND
        (NEW.finalized_case_id,NEW.payload,NEW.version) IS DISTINCT FROM (OLD.finalized_case_id,OLD.payload,OLD.version))
    OR (NEW.payload IS DISTINCT FROM OLD.payload AND NEW.version<>OLD.version+1)
    OR (NEW.payload IS NOT DISTINCT FROM OLD.payload AND NEW.version<>OLD.version) THEN
  RAISE EXCEPTION 'Workspace identity, publication and monotonic versions are retained' USING ERRCODE='42501';
 END IF;
 RETURN NEW;
END $$;
REVOKE ALL ON FUNCTION public.ctm_workspace_version_guard() FROM PUBLIC;
CREATE TRIGGER workspace_version_guard BEFORE INSERT OR UPDATE ON tribunal_historicalworkspace
 FOR EACH ROW EXECUTE FUNCTION public.ctm_workspace_version_guard();
"""


def install(apps, schema_editor):
    if schema_editor.connection.vendor == "postgresql":
        schema_editor.execute(SQL)


def uninstall(apps, schema_editor):
    if schema_editor.connection.vendor == "postgresql":
        schema_editor.execute("DROP TRIGGER workspace_version_guard ON tribunal_historicalworkspace")
        schema_editor.execute("DROP FUNCTION public.ctm_workspace_version_guard()")


class Migration(migrations.Migration):
    dependencies = [("tribunal", "0033_council_revision_and_workspace_versions")]
    operations = [migrations.RunPython(install, uninstall)]
