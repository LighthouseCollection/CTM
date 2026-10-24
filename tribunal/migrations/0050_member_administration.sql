CREATE OR REPLACE FUNCTION public.ctm_core_guard() RETURNS trigger
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
 IF op='member_profile' AND target=OLD.id
    AND public.ctm_actor_role()='admin' AND OLD.role IN ('member','president','secretary','admin') THEN
  IF (to_jsonb(NEW)-ARRAY['first_name','last_name']) IS DISTINCT FROM
     (to_jsonb(OLD)-ARRAY['first_name','last_name'])
     OR length(btrim(NEW.first_name)) NOT BETWEEN 1 AND 150
     OR length(btrim(NEW.last_name)) NOT BETWEEN 1 AND 150
     OR NEW.first_name ~ '[[:cntrl:]]' OR NEW.last_name ~ '[[:cntrl:]]' THEN
   RAISE EXCEPTION 'Member profile corrections can change display names only' USING ERRCODE='42501';
  END IF;
  RETURN NEW;
 END IF;
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

CREATE OR REPLACE FUNCTION public.ctm_staff_writable(resource text,data jsonb) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
 SELECT public.ctm_actor_role()='admin' AND CASE resource
  WHEN 'tribunal' THEN btrim(data->>'code')<>'' AND btrim(data->>'name_en')<>''
  WHEN 'staffmembership' THEN data->>'appointed_by_id'=public.ctm_actor_id()::text
   AND data->>'tribunal_id'=current_setting('ctm.tribunal_id',true) AND data->>'active_until' IS NULL
   AND EXISTS(SELECT 1 FROM public.tribunal_account a WHERE a.id=(data->>'account_id')::uuid AND a.is_active AND a.role<>'applicant')
  WHEN 'staffrole' THEN data->>'role' IN ('president','admin','secretary','member') AND data->>'revoked_at' IS NULL
   AND data->>'granted_by_id'=public.ctm_actor_id()::text
   AND EXISTS(SELECT 1 FROM public.staff_memberships m JOIN public.tribunal_account a ON a.id=m.account_id
    WHERE m.id=(data->>'membership_id')::uuid AND m.tribunal_id::text=current_setting('ctm.tribunal_id',true)
    AND a.is_active AND a.role<>'applicant' AND m.active_from<=statement_timestamp() AND (m.active_until IS NULL OR m.active_until>statement_timestamp()))
  ELSE false END
$$;
