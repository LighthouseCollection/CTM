from django.db import migrations


FORWARD = r'''
CREATE OR REPLACE FUNCTION public.ctm_admin_case_purge_allowed(target uuid) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
 SELECT public.ctm_actor_role()='admin'
   AND target IS NOT NULL
   AND target::text=current_setting('ctm.admin_purge_case',true)
$$;

CREATE OR REPLACE FUNCTION public.ctm_admin_case_purge_active() RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
 SELECT public.ctm_admin_case_purge_allowed(public.ctm_context_uuid('ctm.admin_purge_case'))
$$;

CREATE OR REPLACE FUNCTION public.ctm_reject_history_update() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF public.ctm_migration_caller() OR public.ctm_admin_case_purge_active() THEN RETURN OLD; END IF;
  RAISE EXCEPTION 'CTM historical records cannot be overwritten' USING ERRCODE='23514';
END $$;

CREATE OR REPLACE FUNCTION public.ctm_guard_attendance_transfer_delete() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public AS $$
BEGIN
  IF public.ctm_migration_caller() OR public.ctm_admin_case_purge_active() THEN RETURN OLD; END IF;
  IF OLD.hearing_id IS NOT NULL OR NOT public.ctm_session_transfer_context(OLD.session_id) THEN
    RAISE EXCEPTION 'Attendance history cannot be deleted outside planned reschedule' USING ERRCODE='23514';
  END IF;
  RETURN OLD;
END $$;
CREATE OR REPLACE FUNCTION public.ctm_guard_history_delete() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE disposable boolean=false;
BEGIN
  IF public.ctm_migration_caller() OR public.ctm_admin_case_purge_active() THEN RETURN OLD; END IF;
  CASE TG_TABLE_NAME
    WHEN 'tribunal_answerrevision' THEN
      SELECT a.submitted_at IS NULL AND a.status='draft' INTO disposable FROM tribunal_application a WHERE a.id=OLD.application_id;
    WHEN 'tribunal_fileversion' THEN
      SELECT a.submitted_at IS NULL AND a.status='draft' INTO disposable FROM tribunal_attachment f JOIN tribunal_application a ON a.id=f.application_id WHERE f.id=OLD.attachment_id;
    WHEN 'tribunal_filetechnicalevent', 'tribunal_documenttext' THEN
      SELECT a.submitted_at IS NULL AND a.status='draft' INTO disposable FROM tribunal_fileversion v JOIN tribunal_attachment f ON f.id=v.attachment_id JOIN tribunal_application a ON a.id=f.application_id WHERE v.id=OLD.file_id;
    ELSE disposable=false;
  END CASE;
  IF disposable IS NOT TRUE THEN
    RAISE EXCEPTION 'Submitted records and case history cannot be deleted' USING ERRCODE='23514';
  END IF;
  RETURN OLD;
END $$;

CREATE POLICY admin_case_purge_delete ON public.tribunal_case FOR DELETE
 USING (public.ctm_admin_case_purge_allowed(id));
CREATE POLICY admin_case_purge_delete ON public.tribunal_party FOR DELETE
 USING (public.ctm_admin_case_purge_allowed(case_id));
CREATE POLICY admin_case_purge_delete ON public.tribunal_proceeding FOR DELETE
 USING (public.ctm_admin_case_purge_allowed(case_id));

CREATE OR REPLACE FUNCTION public.ctm_purge_case(target uuid) RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public AS $$
BEGIN
  IF NOT public.ctm_admin_case_purge_allowed(target) THEN
    RAISE EXCEPTION 'Only an administrator may delete a case' USING ERRCODE='42501';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM public.tribunal_case WHERE id=target) THEN
    RAISE EXCEPTION 'Case does not exist' USING ERRCODE='P0002';
  END IF;

  DELETE FROM public.tribunal_transcriptreview WHERE revision_id IN (
    SELECT tr.id FROM public.tribunal_transcriptrevision tr JOIN public.tribunal_recording r ON r.id=tr.recording_id
    WHERE r.appointment_id IN (SELECT id FROM public.tribunal_testimonyappointment WHERE agenda_id IN (SELECT id FROM public.tribunal_agendaitem WHERE case_id=target))
       OR r.report_id IN (SELECT r.id FROM public.tribunal_report r JOIN public.tribunal_reportrequest q ON q.id=r.request_id WHERE q.case_id=target));
  DELETE FROM public.tribunal_transcriptrevision WHERE recording_id IN (
    SELECT id FROM public.tribunal_recording WHERE appointment_id IN (SELECT id FROM public.tribunal_testimonyappointment WHERE agenda_id IN (SELECT id FROM public.tribunal_agendaitem WHERE case_id=target))
       OR report_id IN (SELECT r.id FROM public.tribunal_report r JOIN public.tribunal_reportrequest q ON q.id=r.request_id WHERE q.case_id=target));
  DELETE FROM public.tribunal_processingrun WHERE file_id IN (SELECT id FROM public.tribunal_fileversion WHERE attachment_id IN (SELECT id FROM public.tribunal_attachment WHERE case_id=target OR proceeding_id IN (SELECT id FROM public.tribunal_proceeding WHERE case_id=target) OR application_id IN (SELECT id FROM public.tribunal_application WHERE case_id=target)));
  DELETE FROM public.tribunal_documenttext WHERE file_id IN (SELECT id FROM public.tribunal_fileversion WHERE attachment_id IN (SELECT id FROM public.tribunal_attachment WHERE case_id=target OR proceeding_id IN (SELECT id FROM public.tribunal_proceeding WHERE case_id=target) OR application_id IN (SELECT id FROM public.tribunal_application WHERE case_id=target)));
  DELETE FROM public.tribunal_filetechnicalevent WHERE file_id IN (SELECT id FROM public.tribunal_fileversion WHERE attachment_id IN (SELECT id FROM public.tribunal_attachment WHERE case_id=target OR proceeding_id IN (SELECT id FROM public.tribunal_proceeding WHERE case_id=target) OR application_id IN (SELECT id FROM public.tribunal_application WHERE case_id=target)));
  DELETE FROM public.tribunal_signatureattestation WHERE file_id IN (SELECT id FROM public.tribunal_fileversion WHERE attachment_id IN (SELECT id FROM public.tribunal_attachment WHERE case_id=target OR proceeding_id IN (SELECT id FROM public.tribunal_proceeding WHERE case_id=target) OR application_id IN (SELECT id FROM public.tribunal_application WHERE case_id=target)));
  DELETE FROM public.tribunal_recording WHERE appointment_id IN (SELECT id FROM public.tribunal_testimonyappointment WHERE agenda_id IN (SELECT id FROM public.tribunal_agendaitem WHERE case_id=target)) OR report_id IN (SELECT r.id FROM public.tribunal_report r JOIN public.tribunal_reportrequest q ON q.id=r.request_id WHERE q.case_id=target);
  DELETE FROM public.tribunal_fileversion WHERE attachment_id IN (SELECT id FROM public.tribunal_attachment WHERE case_id=target OR proceeding_id IN (SELECT id FROM public.tribunal_proceeding WHERE case_id=target) OR application_id IN (SELECT id FROM public.tribunal_application WHERE case_id=target));
  DELETE FROM public.tribunal_attachment WHERE case_id=target OR proceeding_id IN (SELECT id FROM public.tribunal_proceeding WHERE case_id=target) OR application_id IN (SELECT id FROM public.tribunal_application WHERE case_id=target);

  DELETE FROM public.tribunal_appointmentresponse WHERE appointment_id IN (SELECT id FROM public.tribunal_testimonyappointment WHERE agenda_id IN (SELECT id FROM public.tribunal_agendaitem WHERE case_id=target));
  DELETE FROM public.testimony_appointment_versions WHERE appointment_id IN (SELECT id FROM public.tribunal_testimonyappointment WHERE agenda_id IN (SELECT id FROM public.tribunal_agendaitem WHERE case_id=target));
  DELETE FROM public.tribunal_testimonyappointment WHERE agenda_id IN (SELECT id FROM public.tribunal_agendaitem WHERE case_id=target);
  DELETE FROM public.tribunal_attendance WHERE hearing_id IN (SELECT id FROM public.tribunal_hearing WHERE agenda_id IN (SELECT id FROM public.tribunal_agendaitem WHERE case_id=target));
  DELETE FROM public.tribunal_hearingoutcome WHERE hearing_id IN (SELECT id FROM public.tribunal_hearing WHERE agenda_id IN (SELECT id FROM public.tribunal_agendaitem WHERE case_id=target));
  DELETE FROM public.tribunal_appealdisposition WHERE hearing_id IN (SELECT id FROM public.tribunal_hearing WHERE agenda_id IN (SELECT id FROM public.tribunal_agendaitem WHERE case_id=target));
  DELETE FROM public.tribunal_hearing WHERE agenda_id IN (SELECT id FROM public.tribunal_agendaitem WHERE case_id=target);
  DELETE FROM public.agenda_transfer_events WHERE case_id=target OR destination_item_id IN (SELECT id FROM public.tribunal_agendaitem WHERE case_id=target);
  DELETE FROM public.tribunal_agendaitem WHERE case_id=target;

  DELETE FROM public.tribunal_completenessreview WHERE submission_id IN (SELECT id FROM public.tribunal_submission WHERE application_id IN (SELECT id FROM public.tribunal_application WHERE case_id=target));
  DELETE FROM public.tribunal_submission WHERE application_id IN (SELECT id FROM public.tribunal_application WHERE case_id=target);
  DELETE FROM public.tribunal_paymentevent WHERE application_id IN (SELECT id FROM public.tribunal_application WHERE case_id=target);
  DELETE FROM public.tribunal_checkoutintent WHERE application_id IN (SELECT id FROM public.tribunal_application WHERE case_id=target);
  DELETE FROM public.tribunal_feeobligation WHERE application_id IN (SELECT id FROM public.tribunal_application WHERE case_id=target);
  DELETE FROM public.tribunal_appealsupplement WHERE application_id IN (SELECT id FROM public.tribunal_application WHERE case_id=target);
  DELETE FROM public.tribunal_answerrevision WHERE application_id IN (SELECT id FROM public.tribunal_application WHERE case_id=target);
  DELETE FROM public.tribunal_application WHERE case_id=target;

  DELETE FROM public.tribunal_messagerecipient WHERE message_id IN (SELECT id FROM public.tribunal_message WHERE case_id=target);
  DELETE FROM public.tribunal_message WHERE case_id=target;
  DELETE FROM public.tribunal_callrecord WHERE case_id=target;
  DELETE FROM public.tribunal_decreerelease WHERE party_id IN (SELECT id FROM public.tribunal_party WHERE case_id=target);
  DELETE FROM public.tribunal_medicalrelease WHERE request_id IN (SELECT id FROM public.tribunal_reportrequest WHERE case_id=target);
  DELETE FROM public.tribunal_reportrevision WHERE report_id IN (SELECT id FROM public.tribunal_report WHERE request_id IN (SELECT id FROM public.tribunal_reportrequest WHERE case_id=target));
  DELETE FROM public.tribunal_report WHERE request_id IN (SELECT id FROM public.tribunal_reportrequest WHERE case_id=target);
  DELETE FROM public.tribunal_reportrequest WHERE case_id=target;
  DELETE FROM public.tribunal_pendingpartylink WHERE case_id=target;
  DELETE FROM public.tribunal_casenote WHERE proceeding_id IN (SELECT id FROM public.tribunal_proceeding WHERE case_id=target);
  DELETE FROM public.tribunal_findingrevision WHERE proceeding_id IN (SELECT id FROM public.tribunal_proceeding WHERE case_id=target);
  DELETE FROM public.tribunal_caseassignment WHERE case_id=target;
  DELETE FROM public.tribunal_opencaseclaim WHERE case_id=target;
  DELETE FROM public.tribunal_historicalworkspace WHERE finalized_case_id=target;
  DELETE FROM public.tribunal_auditevent WHERE case_id=target;
  DELETE FROM public.tribunal_notification WHERE case_id=target;
  DELETE FROM public.tribunal_outbox WHERE case_id=target;
  DELETE FROM public.tribunal_party WHERE case_id=target;
  DELETE FROM public.tribunal_proceeding WHERE case_id=target;
  DELETE FROM public.tribunal_case WHERE id=target;
END $$;

REVOKE ALL ON FUNCTION public.ctm_purge_case(uuid) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.ctm_purge_case(uuid) TO ctm_app;
'''


def remove_retired_demo(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute("SELECT set_config('ctm.admin_purge_case', id::text, true) FROM tribunal_case WHERE number='DEMO-HEARING-TEST-20261022'")
    schema_editor.execute("""
        DELETE FROM tribunal_attendance WHERE hearing_id IN (
          SELECT h.id FROM tribunal_hearing h JOIN tribunal_agendaitem a ON a.id=h.agenda_id
          JOIN tribunal_case c ON c.id=a.case_id WHERE c.number='DEMO-HEARING-TEST-20261022');
        DELETE FROM tribunal_hearingoutcome WHERE hearing_id IN (
          SELECT h.id FROM tribunal_hearing h JOIN tribunal_agendaitem a ON a.id=h.agenda_id
          JOIN tribunal_case c ON c.id=a.case_id WHERE c.number='DEMO-HEARING-TEST-20261022');
        DELETE FROM tribunal_hearing WHERE agenda_id IN (
          SELECT a.id FROM tribunal_agendaitem a JOIN tribunal_case c ON c.id=a.case_id WHERE c.number='DEMO-HEARING-TEST-20261022');
        DELETE FROM tribunal_agendaitem WHERE case_id IN (SELECT id FROM tribunal_case WHERE number='DEMO-HEARING-TEST-20261022');
        DELETE FROM tribunal_caseassignment WHERE case_id IN (SELECT id FROM tribunal_case WHERE number='DEMO-HEARING-TEST-20261022');
        DELETE FROM tribunal_auditevent WHERE case_id IN (SELECT id FROM tribunal_case WHERE number='DEMO-HEARING-TEST-20261022');
        DELETE FROM tribunal_notification WHERE case_id IN (SELECT id FROM tribunal_case WHERE number='DEMO-HEARING-TEST-20261022');
        DELETE FROM tribunal_outbox WHERE case_id IN (SELECT id FROM tribunal_case WHERE number='DEMO-HEARING-TEST-20261022');
        DELETE FROM tribunal_party WHERE case_id IN (SELECT id FROM tribunal_case WHERE number='DEMO-HEARING-TEST-20261022');
        DELETE FROM tribunal_proceeding WHERE case_id IN (SELECT id FROM tribunal_case WHERE number='DEMO-HEARING-TEST-20261022');
        DELETE FROM tribunal_case WHERE number='DEMO-HEARING-TEST-20261022';
    """)


class Migration(migrations.Migration):
    dependencies = [("tribunal", "0056_populate_archived_session_data")]
    operations = [migrations.RunSQL(FORWARD), migrations.RunPython(remove_retired_demo, migrations.RunPython.noop)]

