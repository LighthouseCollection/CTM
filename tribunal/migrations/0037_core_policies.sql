CREATE FUNCTION public.ctm_context_uuid(key text) RETURNS uuid
LANGUAGE plpgsql STABLE SET search_path=pg_catalog,public AS $$
BEGIN RETURN nullif(current_setting(key,true),'')::uuid;
EXCEPTION WHEN invalid_text_representation THEN RETURN NULL; END $$;

CREATE FUNCTION public.ctm_caller() RETURNS text
LANGUAGE sql STABLE SET search_path=pg_catalog,public AS $$
 SELECT coalesce(nullif(current_setting('role',true),'none'),session_user::text)
$$;
CREATE FUNCTION public.ctm_worker_caller() RETURNS boolean
LANGUAGE sql STABLE SET search_path=pg_catalog,public AS $$ SELECT public.ctm_caller()='ctm_worker' $$;
CREATE FUNCTION public.ctm_migration_caller() RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
 SELECT public.ctm_caller()=pg_get_userbyid(relowner) FROM pg_class WHERE oid='public.tribunal_account'::regclass
$$;

CREATE OR REPLACE FUNCTION public.ctm_actor_id() RETURNS uuid
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
DECLARE actor uuid=public.ctm_context_uuid('ctm.actor_id');
BEGIN
 IF public.ctm_worker_caller() AND actor IS DISTINCT FROM public.ctm_paid_filing_actor(public.ctm_context_uuid('ctm.payment_recovery')) THEN RETURN NULL; END IF;
 RETURN actor;
END $$;

CREATE FUNCTION public.ctm_filing_application() RETURNS uuid
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
 SELECT a.id FROM public.tribunal_application a JOIN public.tribunal_account owner ON owner.id=a.owner_id
 JOIN public.tribunal_feeobligation f ON f.application_id=a.id
 WHERE current_setting('ctm.core_operation',true)='filing' AND a.id=public.ctm_context_uuid('ctm.core_target')
 AND a.owner_id=public.ctm_actor_id() AND owner.is_active AND owner.email_verified
 AND a.kind='petition' AND a.status IN ('draft','returned') AND NOT a.duplicate_hold
 AND f.status IN ('paid','waived','historical_exempt')
$$;

CREATE FUNCTION public.ctm_filing_case(target uuid) RETURNS boolean
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
DECLARE answers jsonb; own_dob date; spouse_dob date; married date;
BEGIN
 IF public.ctm_filing_application() IS NOT NULL AND target=public.ctm_context_uuid('ctm.filing_created_case') THEN RETURN true; END IF;
 SELECT r.answers INTO answers FROM public.tribunal_application a JOIN public.tribunal_answerrevision r
 ON r.application_id=a.id AND r.number=a.current_version WHERE a.id=public.ctm_filing_application();
 IF answers IS NULL THEN RETURN false; END IF;
 own_dob=(answers->>'birth_date')::date; spouse_dob=nullif(answers->>'spouse_birth_date','')::date; married=(answers->>'marriage_date')::date;
 IF spouse_dob IS NULL THEN RETURN false; END IF;
 RETURN EXISTS(SELECT 1 FROM public.tribunal_case c WHERE c.id=target AND c.marriage_date=married
 AND c.spouse_dob_low=least(own_dob,spouse_dob) AND c.spouse_dob_high=greatest(own_dob,spouse_dob));
EXCEPTION WHEN invalid_datetime_format OR datetime_field_overflow THEN RETURN false;
END $$;

CREATE FUNCTION public.ctm_close_allowed(target uuid) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
 SELECT CASE current_setting('ctm.close_reason',true)
 WHEN 'petitions_withdrawn' THEN EXISTS(SELECT 1 FROM public.tribunal_application a WHERE a.case_id=target AND a.kind='petition'
   AND a.submitted_at IS NOT NULL AND (a.owner_id=public.ctm_actor_id() OR public.ctm_actor_role()='admin'))
   AND NOT EXISTS(SELECT 1 FROM public.tribunal_party p WHERE p.case_id=target AND p.participating AND p.withdrawn_at IS NULL)
 WHEN 'petition_denied' THEN EXISTS(SELECT 1 FROM public.tribunal_decisionrevision d JOIN public.tribunal_proceeding p ON p.id=d.proceeding_id
   JOIN public.tribunal_presidentialapproval a ON a.decision_id=d.id WHERE p.case_id=target AND d.type='denied' AND a.actor_id=public.ctm_actor_id()
   AND NOT EXISTS(SELECT 1 FROM public.tribunal_decisionrevision newer WHERE newer.proceeding_id=p.id AND newer.number>d.number))
 WHEN 'decree_issued' THEN public.ctm_actor_role() IN ('admin','secretary') AND EXISTS(
   SELECT 1 FROM public.tribunal_decree decree JOIN public.tribunal_decisionrevision d ON d.id=decree.decision_id
    JOIN public.tribunal_proceeding p ON p.id=d.proceeding_id WHERE p.case_id=target AND decree.issued_at IS NOT NULL)
 ELSE false END
$$;

CREATE FUNCTION public.ctm_case_linked(target uuid) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
 SELECT EXISTS(SELECT 1 FROM public.tribunal_party p JOIN public.tribunal_account a ON a.id=p.account_id
 WHERE p.case_id=target AND a.id=public.ctm_actor_id() AND a.is_active AND a.email_verified)
$$;

CREATE FUNCTION public.ctm_historical_context() RETURNS uuid
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
 SELECT w.id FROM public.tribunal_historicalworkspace w WHERE current_setting('ctm.core_operation',true)='historical'
 AND w.id=public.ctm_context_uuid('ctm.core_target') AND w.actor_id=public.ctm_actor_id()
 AND public.ctm_actor_role()='admin' AND w.finalized_case_id IS NULL
$$;

CREATE FUNCTION public.ctm_notice_queue_allowed(data jsonb) RETURNS boolean
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
DECLARE actor uuid=public.ctm_actor_id(); role_name text=public.ctm_actor_role(); kind text=data->>'kind';
 source text=split_part(data->>'key',':',2); target uuid=(data->>'case_id')::uuid; recipient uuid=(data->>'recipient_id')::uuid;
BEGIN
 IF data->>'key' IS DISTINCT FROM kind||':'||source||':'||recipient::text THEN RETURN false; END IF;
 IF role_name='applicant' THEN
  IF kind='submission_received' THEN RETURN recipient=actor AND EXISTS(SELECT 1 FROM public.tribunal_submission s
    JOIN public.tribunal_application a ON a.id=s.application_id WHERE s.id::text=source AND s.actor_id=actor AND a.owner_id=actor AND a.case_id=target); END IF;
  IF kind IN ('intake_submitted','closed_intake_submitted') THEN RETURN EXISTS(SELECT 1 FROM public.tribunal_submission s
    JOIN public.tribunal_application a ON a.id=s.application_id JOIN public.tribunal_account r ON r.id=recipient
    WHERE s.id::text=source AND s.actor_id=actor AND a.owner_id=actor AND a.case_id=target AND r.is_active AND (r.role IN ('admin','secretary') OR (data->>'kind'='closed_intake_submitted' AND EXISTS(SELECT 1 FROM public.tribunal_case c WHERE c.id=target AND c.assigned_member_id=r.id)))); END IF;
  IF NOT EXISTS(SELECT 1 FROM public.tribunal_case c JOIN public.tribunal_account r ON r.id=c.assigned_member_id
    WHERE c.id=target AND r.id=recipient AND r.is_active AND r.role<>'applicant') THEN RETURN false; END IF;
  RETURN CASE kind
   WHEN 'applicant_message' THEN EXISTS(SELECT 1 FROM public.tribunal_message m WHERE m.id::text=source AND m.case_id=target AND m.sender_id=actor)
   WHEN 'answer_changed' THEN EXISTS(SELECT 1 FROM public.tribunal_answerrevision r JOIN public.tribunal_application a ON a.id=r.application_id
     WHERE r.id::text=source AND r.actor_id=actor AND a.owner_id=actor AND a.case_id=target AND a.submitted_at IS NOT NULL AND a.status<>'returned')
   WHEN 'file_uploaded' THEN EXISTS(SELECT 1 FROM public.tribunal_fileversion f JOIN public.tribunal_attachment a ON a.id=f.attachment_id
     WHERE f.id::text=source AND f.actor_id=actor AND a.owner_id=actor AND a.case_id=target)
   WHEN 'appeal_added' THEN EXISTS(SELECT 1 FROM public.tribunal_appealsupplement s JOIN public.tribunal_application a ON a.id=s.application_id
     WHERE s.id::text=source AND s.actor_id=actor AND a.owner_id=actor AND a.case_id=target)
   WHEN 'filing_withdrawn' THEN EXISTS(SELECT 1 FROM public.tribunal_application a WHERE a.id::text=source AND a.owner_id=actor AND a.case_id=target AND a.status='withdrawn')
   WHEN 'report_received' THEN EXISTS(SELECT 1 FROM public.tribunal_report report JOIN public.tribunal_reportrequest r ON r.id=report.request_id
     WHERE report.id::text=source AND report.author_id=actor AND r.case_id=target AND r.state='completed')
   WHEN 'testimony_response' THEN EXISTS(SELECT 1 FROM public.tribunal_appointmentresponse response
     JOIN public.tribunal_testimonyappointment t ON t.id=response.appointment_id JOIN public.tribunal_agendaitem a ON a.id=t.agenda_id
     JOIN public.tribunal_party p ON p.id=t.party_id WHERE response.id::text=source AND p.account_id=actor AND a.case_id=target)
   ELSE false END;
 END IF;
 IF NOT public.ctm_is_council() THEN RETURN false; END IF;
 IF kind='assignment_changed' AND public.ctm_assignment_recorder(actor) THEN
  RETURN EXISTS(SELECT 1 FROM public.tribunal_caseassignment assignment WHERE assignment.id::text=source AND assignment.actor_id=actor AND assignment.case_id=target);
 END IF;
 IF target IS NULL THEN RETURN role_name IN ('admin','secretary') AND kind IN ('questionnaire_updated','paid_filing_review','payment_finance_review'); END IF;
 RETURN (role_name IN ('admin','secretary') OR EXISTS(SELECT 1 FROM public.tribunal_case c WHERE c.id=target AND c.assigned_member_id=actor)
     OR public.ctm_close_allowed(target))
   AND (EXISTS(SELECT 1 FROM public.tribunal_party p WHERE p.case_id=target AND p.account_id=recipient)
     OR EXISTS(SELECT 1 FROM public.tribunal_case c WHERE c.id=target AND c.assigned_member_id=recipient)
     OR (kind IN ('intake_submitted','closed_intake_submitted','manager_authority_review') AND EXISTS(
        SELECT 1 FROM public.tribunal_account a WHERE a.id=recipient AND a.is_active AND a.role IN ('admin','secretary'))));
END $$;

CREATE FUNCTION public.ctm_core_read(resource text,data jsonb) RETURNS boolean
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
DECLARE actor uuid=public.ctm_actor_id(); role_name text=public.ctm_actor_role(); target uuid;
BEGIN
 IF resource='outbox' THEN
  RETURN coalesce(public.ctm_worker_caller() OR role_name IN ('admin','secretary') OR
   public.ctm_anonymous_source_writable('notification',data) OR public.ctm_finance_notice('notification',data) OR
   (actor IS NOT NULL AND (data->>'queued_by_id'=actor::text OR public.ctm_case_writer((data->>'case_id')::uuid))) OR
   (data->>'kind'='finalize_payment' AND data->'payload'->>'intent'=current_setting('ctm.payment_candidate',true)
      AND public.ctm_paid_filing_actor(public.ctm_context_uuid('ctm.payment_candidate')) IS NOT NULL),false);
 END IF;
 IF resource='account' THEN
  RETURN (public.ctm_external_context_valid(true) AND EXISTS(SELECT 1 FROM public.tribunal_reportrequest r
    JOIN public.tribunal_case c ON c.id=r.case_id JOIN public.tribunal_party p ON p.id=r.subject_id
    WHERE r.id=public.ctm_context_uuid('ctm.external_request') AND (c.assigned_member_id=(data->>'id')::uuid OR p.account_id=(data->>'id')::uuid))) OR
   (current_setting('ctm.core_operation',true)='activation' AND public.ctm_context_uuid('ctm.core_target')=actor AND EXISTS(
     SELECT 1 FROM public.tribunal_pendingpartylink p JOIN public.tribunal_account a ON a.email=p.email
     WHERE a.id=actor AND a.is_active AND a.email_verified AND p.state='pending' AND p.actor_id=(data->>'id')::uuid)) OR
   coalesce(data->>'id'=current_setting('ctm.session_account',true) OR data->>'id'=actor::text
   OR role_name IN ('admin','secretary')
   OR (public.ctm_is_council() AND (data->>'role'<>'applicant' OR EXISTS(SELECT 1 FROM public.tribunal_party p WHERE p.account_id=(data->>'id')::uuid)))
   OR (data->>'role'<>'applicant' AND EXISTS(SELECT 1 FROM public.tribunal_case c WHERE c.assigned_member_id=(data->>'id')::uuid AND public.ctm_case_linked(c.id)))
   OR (nullif(current_setting('ctm.provider_subject',true),'') IS NOT NULL AND (
      EXISTS(SELECT 1 FROM public.socialaccount_socialaccount s WHERE s.user_id=(data->>'id')::uuid
       AND s.provider=current_setting('ctm.provider',true) AND s.uid=current_setting('ctm.provider_subject',true))
      OR (current_setting('ctm.provider',true)='microsoft' AND data->>'role'<>'applicant' AND data->>'microsoft_subject'=current_setting('ctm.provider_subject',true))
      OR coalesce(nullif(current_setting('ctm.provider_emails',true),''),'[]')::jsonb ? (data->>'email')))
   OR (data->>'id'=public.ctm_paid_filing_actor(public.ctm_context_uuid('ctm.payment_recovery'))::text)
   OR (data->>'role' IN ('admin','secretary') AND EXISTS(SELECT 1 FROM public.tribunal_checkoutintent i WHERE public.ctm_payment_scope(i.id))),false);
 END IF;
 IF role_name IS NULL THEN
  RETURN public.ctm_external_context_valid(true) AND EXISTS(SELECT 1 FROM public.tribunal_reportrequest r
   WHERE r.id=public.ctm_context_uuid('ctm.external_request') AND CASE resource
    WHEN 'case' THEN r.case_id=(data->>'id')::uuid WHEN 'party' THEN r.subject_id=(data->>'id')::uuid
    WHEN 'proceeding' THEN r.proceeding_id=(data->>'id')::uuid ELSE false END);
 END IF;
 IF resource='person' THEN
  RETURN EXISTS(SELECT 1 FROM public.tribunal_account a WHERE a.id=actor AND a.person_id=(data->>'id')::uuid)
    OR role_name IN ('admin','secretary') OR (public.ctm_is_council() AND EXISTS(
     SELECT 1 FROM public.tribunal_party p WHERE p.person_id=(data->>'id')::uuid)) OR EXISTS(
     SELECT 1 FROM public.tribunal_party p WHERE p.person_id=(data->>'id')::uuid AND public.ctm_filing_case(p.case_id));
 END IF;
 IF resource='case' THEN RETURN public.ctm_is_council() OR public.ctm_case_linked((data->>'id')::uuid) OR public.ctm_filing_case((data->>'id')::uuid)
   OR (current_setting('ctm.core_operation',true)='activation' AND public.ctm_context_uuid('ctm.core_target')=actor AND EXISTS(
     SELECT 1 FROM public.tribunal_pendingpartylink p JOIN public.tribunal_account a ON a.email=p.email
     WHERE a.id=actor AND a.is_active AND a.email_verified AND p.state='pending' AND p.case_id=(data->>'id')::uuid)); END IF;
 IF resource='party' THEN RETURN public.ctm_is_council() OR data->>'account_id'=actor::text OR public.ctm_filing_case((data->>'case_id')::uuid); END IF;
 IF resource='proceeding' THEN RETURN public.ctm_is_council() OR public.ctm_case_linked((data->>'case_id')::uuid) OR public.ctm_filing_case((data->>'case_id')::uuid); END IF;
 IF resource='opencaseclaim' THEN RETURN public.ctm_is_council() OR EXISTS(SELECT 1 FROM public.tribunal_account a WHERE a.id=actor AND a.person_id=(data->>'person_id')::uuid); END IF;
 RETURN false;
END $$;

CREATE FUNCTION public.ctm_core_write(resource text,data jsonb,operation text) RETURNS boolean
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
DECLARE actor uuid=public.ctm_actor_id(); role_name text=public.ctm_actor_role(); op text=current_setting('ctm.core_operation',true);
 target uuid=public.ctm_context_uuid('ctm.core_target'); filing uuid=public.ctm_filing_application(); case_target uuid=(data->>'case_id')::uuid;
BEGIN
 IF operation='lock' THEN
  IF resource IN ('case','proceeding','party','person','account','opencaseclaim') THEN RETURN public.ctm_core_read(resource,data); END IF;
 END IF;
 IF resource='outbox' THEN
  IF operation='insert' THEN
   RETURN (actor IS NOT NULL AND data->>'queued_by_id'=actor::text AND (
    (public.ctm_notice_queue_allowed(data) AND EXISTS(SELECT 1 FROM public.tribunal_notification n WHERE n.key=data->>'key' AND n.recipient_id=(data->>'recipient_id')::uuid
      AND n.kind=data->>'kind' AND n.case_id IS NOT DISTINCT FROM case_target AND n.payload=data->'payload'))
    OR (data->>'kind'='transcribe' AND public.ctm_case_writer(case_target) AND EXISTS(
      SELECT 1 FROM public.tribunal_processingrun r JOIN public.tribunal_fileversion f ON f.id=r.file_id
       JOIN public.tribunal_attachment a ON a.id=f.attachment_id WHERE r.id::text=data->'payload'->>'run'
       AND a.case_id=case_target AND data->>'key'='transcribe:'||r.id::text))
    OR (data->>'kind'='testimony_reminder' AND public.ctm_case_writer(case_target) AND EXISTS(
      SELECT 1 FROM public.testimony_appointment_versions v JOIN public.tribunal_testimonyappointment t ON t.id=v.appointment_id
       JOIN public.tribunal_agendaitem a ON a.id=t.agenda_id JOIN public.tribunal_party p ON p.id=t.party_id
       WHERE data->>'key'='testimony-reminder:'||v.id::text AND a.case_id=case_target AND p.account_id=(data->>'recipient_id')::uuid
       AND t.id::text=data->'payload'->>'appointment' AND v.version=(data->'payload'->>'version')::int))
    OR (data->>'kind'='private_orphan_cleanup' AND op='retention' AND EXISTS(
      SELECT 1 FROM public.tribunal_application a WHERE a.id=target AND a.owner_id=actor AND a.status IN ('deleted','expired') AND a.submitted_at IS NULL))))
    OR ((public.ctm_anonymous_source_writable('notification',data) OR public.ctm_finance_notice('notification',data))
      AND EXISTS(SELECT 1 FROM public.tribunal_notification n WHERE n.key=data->>'key' AND n.recipient_id=(data->>'recipient_id')::uuid
       AND n.kind=data->>'kind' AND n.case_id IS NOT DISTINCT FROM case_target AND n.payload=data->'payload'))
    OR (data->>'kind'='finalize_payment' AND data->>'key'='finalize:'||(data->'payload'->>'intent')
      AND (data->'payload'->>'intent')=current_setting('ctm.payment_candidate',true)
      AND public.ctm_paid_filing_actor(public.ctm_context_uuid('ctm.payment_candidate')) IS NOT NULL);
  END IF;
  RETURN public.ctm_worker_caller() OR role_name IN ('admin','secretary');
 END IF;
 IF resource='account' THEN
  IF operation='insert' THEN
   RETURN (role_name='admin' AND data->>'id'=current_setting('ctm.enroll_account',true) AND data->>'person_id'=current_setting('ctm.enroll_person',true)
      AND data->>'role' IN ('member','president','secretary','admin') AND data->'is_superuser'='false'::jsonb)
    OR (data->>'id'=current_setting('ctm.registration_account',true) AND data->>'person_id'=current_setting('ctm.registration_person',true)
      AND data->>'email'=current_setting('ctm.registration_email',true) AND data->>'role'='applicant' AND data->'is_superuser'='false'::jsonb
      AND data->'email_verified'='true'::jsonb AND current_setting('ctm.provider',true) IN ('google','apple')
      AND coalesce(nullif(current_setting('ctm.provider_emails',true),''),'[]')::jsonb ? (data->>'email'));
  END IF;
  RETURN NOT public.ctm_worker_caller() AND (data->>'id'=actor::text OR role_name IN ('admin','secretary')
    OR (current_setting('ctm.provider',true)='microsoft' AND data->>'microsoft_subject'=current_setting('ctm.provider_subject',true)));
 END IF;
 IF resource='person' THEN
  IF operation='insert' THEN RETURN (role_name='admin' AND data->>'id'=current_setting('ctm.enroll_person',true)) OR
   (data->>'id'=current_setting('ctm.registration_person',true) AND current_setting('ctm.provider',true) IN ('google','apple')); END IF;
  RETURN filing IS NOT NULL AND EXISTS(SELECT 1 FROM public.tribunal_account a WHERE a.id=actor AND a.person_id=(data->>'id')::uuid);
 END IF;
 IF role_name IS NULL THEN RETURN false; END IF;
 IF resource='case' THEN
  IF operation='insert' THEN RETURN (filing IS NOT NULL AND EXISTS(SELECT 1 FROM public.tribunal_application a WHERE a.id=filing AND a.submitted_at IS NULL) AND public.ctm_actor_role()='applicant' AND data->>'status'='open' AND data->>'origin'='new'
       AND data->>'assigned_member_id' IS NULL AND data->>'closed_at' IS NULL AND data->>'number' ~ '^[0-9]{8}-[0-9]{2}$') OR EXISTS(
    SELECT 1 FROM public.tribunal_historicalworkspace w WHERE w.id=public.ctm_historical_context() AND data->>'origin'='historical'
     AND data->>'number'=w.payload->>'number' AND data->>'status'=w.payload->>'status'); END IF;
  RETURN (op='assignment' AND target=(data->>'id')::uuid AND data->>'status'='open'
      AND public.ctm_assignment_recorder(actor) AND public.ctm_assignment_president(public.ctm_context_uuid('ctm.assignment_president'))
      AND data->>'assigned_member_id'=current_setting('ctm.assignment_member',true))
    OR (op='close' AND target=(data->>'id')::uuid AND public.ctm_close_allowed(target))
    OR (current_setting('ctm.result_choice',true)='accept' AND EXISTS(SELECT 1 FROM public.tribunal_application a
      WHERE a.id=public.ctm_context_uuid('ctm.council_result') AND a.case_id=(data->>'id')::uuid
      AND public.ctm_council_result_allowed(a.id,public.ctm_context_uuid('ctm.result_hearing'),'accept')));
 END IF;
 IF resource='party' THEN
  RETURN (filing IS NOT NULL AND public.ctm_filing_case(case_target) AND data->>'account_id'=actor::text
      AND EXISTS(SELECT 1 FROM public.tribunal_account a WHERE a.id=actor AND a.person_id=(data->>'person_id')::uuid))
    OR (op='onboarding' AND target=case_target AND role_name IN ('admin','secretary') AND EXISTS(
      SELECT 1 FROM public.tribunal_account a WHERE a.id=(data->>'account_id')::uuid AND a.person_id=(data->>'person_id')::uuid
        AND a.role='applicant' AND a.is_active AND a.email_verified))
    OR (role_name='admin' AND EXISTS(SELECT 1 FROM public.tribunal_historicalworkspace w JOIN public.tribunal_case c
      ON c.number=w.payload->>'number' AND c.origin='historical' WHERE w.id=public.ctm_historical_context() AND c.id=case_target))
    OR (op='withdraw' AND EXISTS(SELECT 1 FROM public.tribunal_application a WHERE a.id=target AND a.party_id=(data->>'id')::uuid
      AND (a.owner_id=actor OR role_name='admin') AND a.status='withdrawn'))
    OR (current_setting('ctm.result_choice',true)='accept' AND EXISTS(SELECT 1 FROM public.tribunal_application a
      WHERE a.id=public.ctm_context_uuid('ctm.council_result') AND a.case_id=case_target
       AND a.owner_id=(data->>'account_id')::uuid AND public.ctm_is_council()));
 END IF;
 IF resource='proceeding' THEN
  IF operation='insert' THEN RETURN (filing IS NOT NULL AND EXISTS(SELECT 1 FROM public.tribunal_application a WHERE a.id=filing AND a.submitted_at IS NULL) AND public.ctm_filing_case(case_target) AND data->>'kind'='initial' AND (data->>'sequence')::int=0)
    OR EXISTS(SELECT 1 FROM public.tribunal_historicalworkspace w JOIN public.tribunal_case c ON c.number=w.payload->>'number' AND c.origin='historical' WHERE w.id=public.ctm_historical_context() AND c.id=case_target) OR (current_setting('ctm.result_choice',true)='accept' AND public.ctm_is_council()
     AND EXISTS(SELECT 1 FROM public.tribunal_application a WHERE a.id=public.ctm_context_uuid('ctm.council_result') AND a.case_id=case_target)); END IF;
  RETURN op='close' AND target=case_target AND public.ctm_close_allowed(case_target);
 END IF;
 IF resource='opencaseclaim' THEN
  IF operation='delete' THEN RETURN op='close' AND target=case_target AND EXISTS(SELECT 1 FROM public.tribunal_case c WHERE c.id=case_target AND c.status='closed'); END IF;
  RETURN EXISTS(SELECT 1 FROM public.tribunal_party p JOIN public.tribunal_case c ON c.id=p.case_id
    WHERE p.person_id=(data->>'person_id')::uuid AND p.case_id=case_target AND c.status='open')
   AND (filing IS NOT NULL OR (op='onboarding' AND target=case_target AND role_name IN ('admin','secretary'))
    OR EXISTS(SELECT 1 FROM public.tribunal_historicalworkspace w JOIN public.tribunal_case c ON c.number=w.payload->>'number' AND c.origin='historical' WHERE w.id=public.ctm_historical_context() AND c.id=case_target) OR (current_setting('ctm.result_choice',true)='accept' AND public.ctm_is_council()));
 END IF;
 RETURN false;
END $$;

CREATE FUNCTION public.ctm_core_guard() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public AS $$
DECLARE op text=current_setting('ctm.core_operation',true); target uuid=public.ctm_context_uuid('ctm.core_target');
BEGIN
 IF TG_TABLE_NAME='tribunal_outbox' AND TG_OP='INSERT' THEN NEW.queued_by_id=public.ctm_actor_id(); RETURN NEW; END IF;
 IF TG_TABLE_NAME='tribunal_case' AND TG_OP='INSERT' AND public.ctm_filing_application() IS NOT NULL THEN
  PERFORM set_config('ctm.filing_created_case',NEW.id::text,true);
 END IF;
 IF TG_OP='INSERT' THEN RETURN NEW; END IF;
 IF TG_TABLE_NAME='tribunal_outbox' THEN
  IF NEW.queued_by_id IS DISTINCT FROM OLD.queued_by_id THEN RAISE EXCEPTION 'Queue actor is retained' USING ERRCODE='42501'; END IF;
  IF NOT public.ctm_migration_caller() AND NOT public.ctm_worker_caller() THEN
   IF (to_jsonb(NEW)-ARRAY['due_at','payload']) IS DISTINCT FROM (to_jsonb(OLD)-ARRAY['due_at','payload'])
     AND NOT (op='queue_retry' AND target=OLD.id AND public.ctm_actor_role() IN ('admin','secretary')
       AND (to_jsonb(NEW)-ARRAY['due_at','last_error','lease_until','lease_token']) IS NOT DISTINCT FROM (to_jsonb(OLD)-ARRAY['due_at','last_error','lease_until','lease_token'])
       AND NEW.last_error='' AND NEW.lease_until IS NULL AND NEW.lease_token IS NULL
       AND OLD.delivered_at IS NULL AND OLD.discarded_at IS NULL AND (OLD.lease_until IS NULL OR OLD.lease_until<=statement_timestamp())) THEN
    RAISE EXCEPTION 'Only the worker records delivery outcomes' USING ERRCODE='42501';
   END IF;
  END IF;
  RETURN NEW;
 END IF;
 IF TG_TABLE_NAME='tribunal_person' AND NOT public.ctm_migration_caller() THEN
  IF (NEW.id,NEW.created_at) IS DISTINCT FROM (OLD.id,OLD.created_at) OR NOT EXISTS(
    SELECT 1 FROM public.tribunal_application a JOIN public.tribunal_answerrevision r ON r.application_id=a.id AND r.number=a.current_version
     WHERE a.id=public.ctm_filing_application() AND NEW.first_name=r.answers->>'first_name' AND NEW.last_name=r.answers->>'last_name'
       AND NEW.birth_date=(r.answers->>'birth_date')::date AND NEW.gender=r.answers->>'gender') THEN
   RAISE EXCEPTION 'Person corrections require the bound filing snapshot' USING ERRCODE='42501';
  END IF;
  RETURN NEW;
 END IF;
 IF TG_TABLE_NAME='tribunal_account' THEN
  IF NOT public.ctm_migration_caller() THEN
   IF (to_jsonb(NEW)-ARRAY['ui_language','notification_language','last_login','is_active','email_verified']) IS DISTINCT FROM
      (to_jsonb(OLD)-ARRAY['ui_language','notification_language','last_login','is_active','email_verified']) THEN
    RAISE EXCEPTION 'Identity and authorization cannot be changed through preferences' USING ERRCODE='42501'; END IF;
   IF NEW.is_active IS DISTINCT FROM OLD.is_active AND NOT (op='account_status' AND target=OLD.id AND public.ctm_actor_role() IN ('admin','secretary')
     AND (NEW.is_active OR (OLD.id<>public.ctm_actor_id() AND (OLD.role<>'admin' OR EXISTS(
      SELECT 1 FROM public.tribunal_account a WHERE a.role='admin' AND a.is_active AND a.id<>OLD.id))))) THEN
    RAISE EXCEPTION 'Account status needs guarded administrative authority' USING ERRCODE='42501'; END IF;
   IF NEW.email_verified IS DISTINCT FROM OLD.email_verified AND NOT (NEW.email_verified AND current_setting('ctm.provider',true)='microsoft'
      AND OLD.microsoft_subject=current_setting('ctm.provider_subject',true)) THEN
    RAISE EXCEPTION 'Verification requires the validated provider' USING ERRCODE='42501'; END IF;
   IF (NEW.ui_language NOT IN ('en','ar') OR NEW.notification_language NOT IN ('en','ar')) THEN RAISE EXCEPTION 'Unsupported preferences' USING ERRCODE='23514'; END IF;
  END IF;
  RETURN NEW;
 END IF;
 IF TG_TABLE_NAME='tribunal_case' THEN
  IF (NEW.id,NEW.created_at,NEW.number,NEW.origin,NEW.marriage_date,NEW.spouse_dob_low,NEW.spouse_dob_high) IS DISTINCT FROM
     (OLD.id,OLD.created_at,OLD.number,OLD.origin,OLD.marriage_date,OLD.spouse_dob_low,OLD.spouse_dob_high) THEN
   RAISE EXCEPTION 'Case source identity is retained' USING ERRCODE='42501'; END IF;
  IF NOT public.ctm_migration_caller() THEN
   IF op='assignment' AND (to_jsonb(NEW)-'assigned_member_id') IS DISTINCT FROM (to_jsonb(OLD)-'assigned_member_id') THEN
    RAISE EXCEPTION 'Assignment cannot alter case lifecycle' USING ERRCODE='42501'; END IF;
   IF (op='close' OR current_setting('ctm.result_choice',true)='accept') AND
       (to_jsonb(NEW)-ARRAY['status','closed_at']) IS DISTINCT FROM (to_jsonb(OLD)-ARRAY['status','closed_at']) THEN
    RAISE EXCEPTION 'Lifecycle cannot alter case ownership or assignment' USING ERRCODE='42501'; END IF;
   IF op='close' AND (NEW.status<>'closed' OR NEW.closed_at IS NULL) THEN
    RAISE EXCEPTION 'Closure must retain its timestamp' USING ERRCODE='42501'; END IF;
  END IF;
 END IF;
 IF TG_TABLE_NAME='tribunal_party' THEN
 IF (NEW.id,NEW.created_at,NEW.case_id,NEW.person_id,NEW.account_id,NEW.slot) IS DISTINCT FROM
    (OLD.id,OLD.created_at,OLD.case_id,OLD.person_id,OLD.account_id,OLD.slot) THEN
  RAISE EXCEPTION 'Party identity requires a separate attributed consolidation' USING ERRCODE='42501'; END IF;
 END IF;
 IF TG_TABLE_NAME='tribunal_proceeding' THEN
 IF (NEW.id,NEW.created_at,NEW.case_id,NEW.kind,NEW.sequence) IS DISTINCT FROM
    (OLD.id,OLD.created_at,OLD.case_id,OLD.kind,OLD.sequence) THEN
  RAISE EXCEPTION 'Proceeding identity is retained' USING ERRCODE='42501'; END IF;
 END IF;
 RETURN NEW;
END $$;

CREATE FUNCTION public.ctm_applicant_parties(target uuid) RETURNS jsonb
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
 SELECT coalesce(jsonb_agg(jsonb_build_object('id',p.id,'name',p.name,'is_self',p.account_id=public.ctm_actor_id(),
   'can_receive',p.account_id IS NOT NULL,'reference',CASE WHEN p.account_id=public.ctm_actor_id() THEN p.reference ELSE NULL END) ORDER BY p.slot),'[]'::jsonb)
 FROM public.tribunal_party p WHERE p.case_id=target AND public.ctm_actor_role()='applicant' AND public.ctm_case_linked(target)
$$;

CREATE FUNCTION public.ctm_delivery_destination(target uuid) RETURNS jsonb
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

CREATE FUNCTION public.ctm_delay_digest(target uuid,deadline timestamptz) RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public AS $$
BEGIN
 IF NOT public.ctm_migration_caller() AND NOT (public.ctm_case_linked(target) AND public.ctm_actor_role()='applicant'
   AND deadline BETWEEN statement_timestamp()+interval '9 minutes' AND statement_timestamp()+interval '11 minutes') THEN
  RAISE EXCEPTION 'Own editing digest context required' USING ERRCODE='42501'; END IF;
 UPDATE public.tribunal_outbox SET due_at=deadline WHERE case_id=target AND delivered_at IS NULL AND discarded_at IS NULL
   AND lease_until IS NULL AND kind IN ('answer_changed','file_uploaded','appeal_added');
END $$;
