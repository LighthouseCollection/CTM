-- #176 / D-0044: admin, president and secretary may delete a case.
--
-- The history triggers (ctm_reject_history_update, ctm_guard_history_delete,
-- ctm_guard_attendance_transfer_delete, 0069's answer guard) and the case,
-- party and proceeding delete policies all ask ctm_admin_case_purge_active() or
-- ctm_admin_case_purge_allowed(). Before this migration a caller with an admin
-- actor opened them by setting ctm.admin_purge_case. Now they open only for a
-- grant row that ctm_delete_case writes in the same transaction, in a table no
-- runtime role can touch.
CREATE TABLE public.ctm_case_delete_grant(
  case_id uuid PRIMARY KEY,
  xact xid8 NOT NULL DEFAULT pg_current_xact_id()
);
REVOKE ALL ON TABLE public.ctm_case_delete_grant FROM PUBLIC;
ALTER TABLE public.ctm_case_delete_grant ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ctm_case_delete_grant FORCE ROW LEVEL SECURITY;
CREATE POLICY ctm_case_delete_grant_same_xact ON public.ctm_case_delete_grant
  USING (xact=pg_current_xact_id()) WITH CHECK (xact=pg_current_xact_id());

CREATE OR REPLACE FUNCTION public.ctm_admin_case_purge_allowed(target uuid) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
 SELECT target IS NOT NULL AND EXISTS(SELECT 1 FROM public.ctm_case_delete_grant g
   WHERE g.case_id=target AND g.xact=pg_current_xact_id())
$$;

CREATE OR REPLACE FUNCTION public.ctm_admin_case_purge_active() RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
 SELECT EXISTS(SELECT 1 FROM public.ctm_case_delete_grant g WHERE g.xact=pg_current_xact_id())
$$;

CREATE FUNCTION public.ctm_delete_case(target uuid, reason text) RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public AS $$
DECLARE
  actor uuid=public.ctm_actor_id();
  case_number text;
BEGIN
  -- ctm_actor_role() is NULL for an inactive or unknown actor.
  IF actor IS NULL OR public.ctm_actor_role() IS NULL OR public.ctm_actor_role() NOT IN ('admin','president','secretary') THEN
    RAISE EXCEPTION 'Only an administrator, president or secretary may delete a case' USING ERRCODE='42501';
  END IF;
  IF reason IS NOT NULL AND (length(reason)>500 OR reason ~ '[[:cntrl:]]') THEN
    RAISE EXCEPTION 'The reason must be plain text up to 500 characters' USING ERRCODE='22023';
  END IF;
  SELECT c.number INTO case_number FROM public.tribunal_case c WHERE c.id=target FOR UPDATE;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'Case does not exist' USING ERRCODE='P0002';
  END IF;
  INSERT INTO public.ctm_case_delete_grant(case_id) VALUES (target);

  DELETE FROM public.tribunal_decreerelease WHERE party_id IN (SELECT id FROM public.tribunal_party WHERE case_id=target) OR decree_id IN (SELECT id FROM public.tribunal_decree WHERE decision_id IN (SELECT id FROM public.tribunal_decisionrevision WHERE proceeding_id IN (SELECT id FROM public.tribunal_proceeding WHERE case_id=target)));
  DELETE FROM public.tribunal_decree WHERE decision_id IN (SELECT id FROM public.tribunal_decisionrevision WHERE proceeding_id IN (SELECT id FROM public.tribunal_proceeding WHERE case_id=target));
  DELETE FROM public.tribunal_transcriptreview WHERE revision_id IN (
  DELETE FROM public.tribunal_transcriptrevision WHERE recording_id IN (
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
  DELETE FROM public.tribunal_medicalrelease WHERE request_id IN (SELECT id FROM public.tribunal_reportrequest WHERE case_id=target);
  DELETE FROM public.tribunal_reportrevision WHERE report_id IN (SELECT id FROM public.tribunal_report WHERE request_id IN (SELECT id FROM public.tribunal_reportrequest WHERE case_id=target));
  DELETE FROM public.tribunal_report WHERE request_id IN (SELECT id FROM public.tribunal_reportrequest WHERE case_id=target);
  DELETE FROM public.tribunal_reportrequest WHERE case_id=target;
  DELETE FROM public.tribunal_pendingpartylink WHERE case_id=target;
  DELETE FROM public.tribunal_noterevision WHERE note_id IN (SELECT id FROM public.tribunal_casenote WHERE proceeding_id IN (SELECT id FROM public.tribunal_proceeding WHERE case_id=target));
  DELETE FROM public.tribunal_casenote WHERE proceeding_id IN (SELECT id FROM public.tribunal_proceeding WHERE case_id=target);
  DELETE FROM public.tribunal_vote WHERE decision_id IN (SELECT id FROM public.tribunal_decisionrevision WHERE proceeding_id IN (SELECT id FROM public.tribunal_proceeding WHERE case_id=target));
  DELETE FROM public.tribunal_presidentialapproval WHERE decision_id IN (SELECT id FROM public.tribunal_decisionrevision WHERE proceeding_id IN (SELECT id FROM public.tribunal_proceeding WHERE case_id=target));
  DELETE FROM public.tribunal_decisionrevision WHERE proceeding_id IN (SELECT id FROM public.tribunal_proceeding WHERE case_id=target);
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

  DELETE FROM public.ctm_case_delete_grant WHERE case_id=target;
  -- The only trace (D-0044): case number, who, when and the optional reason. No case content.
  INSERT INTO public.tribunal_auditevent(id,created_at,actor_id,action,source,source_id,case_id,metadata)
  VALUES (gen_random_uuid(),clock_timestamp(),actor,'case_deleted','tribunal.case',target,NULL,
          jsonb_build_object('case_number',case_number,'reason',reason));
END $$;
REVOKE ALL ON FUNCTION public.ctm_delete_case(uuid,text) FROM PUBLIC;

-- Kept for the existing admin service until the backend moves to ctm_delete_case.
CREATE OR REPLACE FUNCTION public.ctm_purge_case(target uuid) RETURNS void
LANGUAGE sql SECURITY DEFINER SET search_path=pg_catalog,public AS $$
 SELECT public.ctm_delete_case(target, NULL)
$$;
