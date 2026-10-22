CREATE FUNCTION public.ctm_account_status_source(data jsonb) RETURNS boolean
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
DECLARE e public.tribunal_auditevent; a public.tribunal_account; config public.tribunal_settingrevision;
 item jsonb; chosen jsonb; matches integer=0; language text; subject_key text; body_key text;
BEGIN
 SELECT * INTO e FROM public.tribunal_auditevent WHERE id=(data->'payload'->>'account_event')::uuid;
 IF NOT FOUND OR e.source<>'tribunal.account' OR e.case_id IS NOT NULL OR data->>'case_id' IS NOT NULL
   OR e.action NOT IN ('account_suspended','account_reactivated') OR e.action IS DISTINCT FROM data->>'kind'
   OR e.actor_id::text IS DISTINCT FROM data->>'queued_by_id' OR e.source_id::text IS DISTINCT FROM data->>'recipient_id'
   OR data->>'key' IS DISTINCT FROM e.action||':'||e.id::text||':'||e.source_id::text THEN RETURN false; END IF;
 SELECT * INTO a FROM public.tribunal_account WHERE id=e.source_id AND role='applicant';
 IF NOT FOUND OR a.is_active IS DISTINCT FROM (e.action='account_reactivated')
   OR e.metadata->'after' IS DISTINCT FROM to_jsonb(a.is_active)
   OR e.metadata->'before' IS DISTINCT FROM to_jsonb(NOT a.is_active)
   OR e.metadata->'status_version' IS DISTINCT FROM to_jsonb((SELECT count(*) FROM public.tribunal_auditevent
       WHERE source='tribunal.account' AND source_id=a.id AND action IN ('account_suspended','account_reactivated'))) THEN RETURN false; END IF;
 language=e.metadata->>'notification_language';
 IF language IS NULL OR language NOT IN ('en','ar') THEN RETURN false; END IF;
 SELECT * INTO config FROM public.tribunal_settingrevision WHERE key='email_templates' AND number=(e.metadata->>'template_version')::integer;
 IF NOT FOUND OR jsonb_typeof(config.value->'templates') IS DISTINCT FROM 'array'
   OR NOT public.ctm_configuration_safe(config.value) OR octet_length(config.value::text)>100000 THEN RETURN false; END IF;
 FOR item IN SELECT value FROM jsonb_array_elements(config.value->'templates') LOOP
  IF item->>'code'=e.action THEN chosen=item; matches=matches+1; END IF;
 END LOOP;
 subject_key='subject_'||language; body_key='body_'||language;
 IF matches<>1 OR jsonb_typeof(chosen->subject_key) IS DISTINCT FROM 'string'
   OR jsonb_typeof(chosen->body_key) IS DISTINCT FROM 'string'
   OR btrim(chosen->>subject_key)='' OR btrim(chosen->>body_key)=''
   OR length(chosen->>subject_key)>300 OR length(chosen->>body_key)>20000
   OR chosen->>subject_key ~ E'[\\r\\n]' THEN RETURN false; END IF;
 RETURN data->'payload'=jsonb_build_object('account_event',e.id,'language',language,
   'template_version',config.number,'subject',chosen->>subject_key,'body',chosen->>body_key);
EXCEPTION WHEN invalid_text_representation OR numeric_value_out_of_range THEN RETURN false;
END $$;
REVOKE ALL ON FUNCTION public.ctm_account_status_source(jsonb) FROM PUBLIC;

CREATE FUNCTION public.ctm_account_status_notice_allowed(data jsonb) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
 SELECT coalesce(public.ctm_actor_role() IN ('admin','secretary')
 AND current_setting('ctm.core_operation',true)='account_status'
 AND data->>'recipient_id'=current_setting('ctm.core_target',true)
 AND public.ctm_account_status_source(data||jsonb_build_object('queued_by_id',public.ctm_actor_id())),false)
$$;
REVOKE ALL ON FUNCTION public.ctm_account_status_notice_allowed(jsonb) FROM PUBLIC;
CREATE POLICY account_status_notice_insert ON public.tribunal_notification FOR INSERT
 WITH CHECK (public.ctm_account_status_notice_allowed(to_jsonb(tribunal_notification)));
CREATE POLICY account_status_notice_insert ON public.tribunal_outbox FOR INSERT
 WITH CHECK (public.ctm_account_status_notice_allowed(to_jsonb(tribunal_outbox)));

CREATE OR REPLACE FUNCTION public.ctm_delivery_destination(target uuid) RETURNS jsonb
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
DECLARE result jsonb; job public.tribunal_outbox;
BEGIN
 IF NOT public.ctm_worker_caller() AND NOT public.ctm_migration_caller() THEN RAISE EXCEPTION 'Worker only' USING ERRCODE='42501'; END IF;
 SELECT * INTO job FROM public.tribunal_outbox WHERE id=target;
 IF job.kind IN ('account_suspended','account_reactivated') THEN
  IF NOT public.ctm_account_status_source(to_jsonb(job)) THEN RETURN NULL; END IF;
  SELECT jsonb_build_object('email',a.email,'is_active',a.is_active,'email_verified',a.email_verified,'role',a.role,
    'status_notice',true,'subject',job.payload->>'subject','body',job.payload->>'body') INTO result
   FROM public.tribunal_account a WHERE a.id=job.recipient_id;
  RETURN result;
 END IF;
 SELECT jsonb_build_object('email',a.email,'is_active',a.is_active,'email_verified',a.email_verified,'role',a.role)
 INTO result FROM public.tribunal_outbox o LEFT JOIN public.tribunal_case c ON c.id=o.case_id JOIN public.tribunal_account a ON a.id=CASE
 WHEN o.case_id IS NOT NULL AND o.kind IN ('answer_changed','file_uploaded','appeal_added','report_received','filing_withdrawn','testimony_response','applicant_message') THEN c.assigned_member_id ELSE o.recipient_id END
 WHERE o.id=target;
 RETURN result;
END $$;
