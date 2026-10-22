from pathlib import Path
from django.db import migrations, models

ORIGINAL_DESTINATION = """
CREATE OR REPLACE FUNCTION public.ctm_delivery_destination(target uuid) RETURNS jsonb
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
DECLARE result jsonb;
BEGIN
 IF NOT public.ctm_worker_caller() AND NOT public.ctm_migration_caller() THEN RAISE EXCEPTION 'Worker only' USING ERRCODE='42501'; END IF;
 SELECT jsonb_build_object('email',a.email,'is_active',a.is_active,'email_verified',a.email_verified,'role',a.role)
 INTO result FROM public.tribunal_outbox o LEFT JOIN public.tribunal_case c ON c.id=o.case_id JOIN public.tribunal_account a ON a.id=CASE
 WHEN o.case_id IS NOT NULL AND o.kind IN ('answer_changed','file_uploaded','appeal_added','report_received','filing_withdrawn','testimony_response','applicant_message') THEN c.assigned_member_id ELSE o.recipient_id END
 WHERE o.id=target;
 RETURN result;
END $$;
"""


def install(apps, schema_editor):
    if schema_editor.connection.vendor!='postgresql':
        return
    schema_editor.execute(Path(__file__).with_suffix('.sql').read_text())
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("SELECT rolname FROM pg_roles WHERE rolname IN ('ctm_app','ctm_worker')")
        roles=[row[0] for row in cursor.fetchall()]
    for role in roles:
        schema_editor.execute(f'GRANT EXECUTE ON FUNCTION public.ctm_account_status_notice_allowed(jsonb) TO {schema_editor.quote_name(role)}')


def uninstall(apps, schema_editor):
    if schema_editor.connection.vendor!='postgresql':
        return
    schema_editor.execute(ORIGINAL_DESTINATION)
    schema_editor.execute('DROP POLICY account_status_notice_insert ON public.tribunal_notification')
    schema_editor.execute('DROP POLICY account_status_notice_insert ON public.tribunal_outbox')
    schema_editor.execute('DROP FUNCTION public.ctm_account_status_notice_allowed(jsonb)')
    schema_editor.execute('DROP FUNCTION public.ctm_account_status_source(jsonb)')


class Migration(migrations.Migration):
    dependencies=[('tribunal','0039_filing_case_snapshot_guard')]
    operations=[migrations.AddIndex(model_name='auditevent',index=models.Index(fields=['source','source_id','action'],name='account_status_events_idx')),
                migrations.RunPython(install,uninstall)]
