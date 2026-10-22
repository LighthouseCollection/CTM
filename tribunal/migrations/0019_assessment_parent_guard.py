from django.db import migrations

SQL = """
CREATE FUNCTION public.ctm_guard_report_parent() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public AS $$
DECLARE parent_case uuid; parent_kind text;
BEGIN
 IF TG_TABLE_NAME='tribunal_report' THEN
  IF NEW.request_id IS DISTINCT FROM OLD.request_id THEN
   RAISE EXCEPTION 'Report request identity is retained' USING ERRCODE='42501';
  END IF;
  RETURN NEW;
 END IF;
 IF TG_OP='UPDATE' THEN
  IF (NEW.case_id,NEW.proceeding_id,NEW.subject_id,NEW.author_id,NEW.kind,NEW.parent_report_id)
      IS DISTINCT FROM (OLD.case_id,OLD.proceeding_id,OLD.subject_id,OLD.author_id,OLD.kind,OLD.parent_report_id) THEN
   RAISE EXCEPTION 'Report request scope and parent are retained' USING ERRCODE='42501';
  END IF;
  RETURN NEW;
 END IF;
 IF NEW.parent_report_id IS NOT NULL THEN
  SELECT request.case_id,request.kind INTO parent_case,parent_kind
   FROM public.tribunal_report report JOIN public.tribunal_reportrequest request ON request.id=report.request_id
   WHERE report.id=NEW.parent_report_id;
  IF parent_case IS DISTINCT FROM NEW.case_id OR (parent_kind IN ('medical','psychological') AND NEW.kind NOT IN ('medical','psychological')) THEN
   RAISE EXCEPTION 'Follow-up parent is outside the permitted case or assessment scope' USING ERRCODE='42501';
  END IF;
 END IF;
 RETURN NEW;
END
$$;
REVOKE ALL ON FUNCTION public.ctm_guard_report_parent() FROM PUBLIC;
CREATE TRIGGER preserve_report_parent BEFORE INSERT OR UPDATE ON public.tribunal_reportrequest FOR EACH ROW EXECUTE FUNCTION public.ctm_guard_report_parent();
CREATE TRIGGER preserve_report_request BEFORE UPDATE ON public.tribunal_report FOR EACH ROW EXECUTE FUNCTION public.ctm_guard_report_parent();
"""


def install(apps, schema_editor):
    if schema_editor.connection.vendor == 'postgresql':
        schema_editor.execute(SQL)


def uninstall(apps, schema_editor):
    if schema_editor.connection.vendor == 'postgresql':
        schema_editor.execute('DROP TRIGGER preserve_report_request ON public.tribunal_report')
        schema_editor.execute('DROP TRIGGER preserve_report_parent ON public.tribunal_reportrequest')
        schema_editor.execute('DROP FUNCTION public.ctm_guard_report_parent()')


class Migration(migrations.Migration):
    dependencies = [('tribunal', '0018_council_library_privacy')]
    operations = [migrations.RunPython(install, uninstall)]
