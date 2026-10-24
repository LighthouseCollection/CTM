CREATE FUNCTION public.ctm_recording_file_allowed(target uuid,source uuid) RETURNS boolean
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
BEGIN
 RETURN coalesce(target=public.ctm_context_uuid('ctm.recording_request') AND source=public.ctm_context_uuid('ctm.recording_file')
 AND current_setting('ctm.recording_acknowledged',true)='true'
 AND nullif(current_setting('ctm.recording_date',true),'')::date<=(statement_timestamp() AT TIME ZONE 'America/Los_Angeles')::date
 AND EXISTS(SELECT 1 FROM public.tribunal_reportrequest r JOIN public.tribunal_proceeding p ON p.id=r.proceeding_id
 JOIN public.tribunal_case c ON c.id=r.case_id JOIN public.tribunal_attachment a ON a.case_id=c.id AND a.proceeding_id=p.id
 JOIN public.tribunal_fileversion f ON f.attachment_id=a.id
 WHERE r.id=target AND f.id=source AND r.kind='external_priest' AND r.state='sent' AND r.sent_at IS NOT NULL
 AND p.case_id=c.id AND p.status='open' AND c.status='open' AND public.ctm_case_writer(c.id)
 AND a.owner_id IS NULL AND a.application_id IS NULL AND a.report_request_id IS NULL
 AND a.visibility='council' AND a.category='AUDIO' AND (f.mime_type LIKE 'audio/%%' OR f.mime_type LIKE 'video/%%')
 AND NOT EXISTS(SELECT 1 FROM public.tribunal_fileversion newer WHERE newer.attachment_id=a.id AND newer.number>f.number)
 AND NOT EXISTS(SELECT 1 FROM public.tribunal_recording old WHERE old.file_id=f.id)
 AND (SELECT e.result FROM public.tribunal_filetechnicalevent e WHERE e.file_id=f.id AND e.task='scan'
 ORDER BY e.created_at DESC,e.id DESC LIMIT 1)='clean'),false);
EXCEPTION WHEN invalid_datetime_format OR datetime_field_overflow THEN RETURN false;
END $$;
REVOKE ALL ON FUNCTION public.ctm_recording_file_allowed(uuid,uuid) FROM PUBLIC;

CREATE FUNCTION public.ctm_recording_capture_allowed(data jsonb,operation text) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
 SELECT EXISTS(SELECT 1 FROM public.tribunal_report report JOIN public.tribunal_reportrequest r ON r.id=report.request_id
 JOIN public.tribunal_reportrevision revision ON revision.report_id=report.id AND revision.number=1
 JOIN public.tribunal_fileversion f ON f.id=(data->>'file_id')::uuid JOIN public.tribunal_attachment a ON a.id=f.attachment_id
 JOIN public.tribunal_proceeding p ON p.id=r.proceeding_id JOIN public.tribunal_case c ON c.id=r.case_id
 WHERE report.id=(data->>'report_id')::uuid AND report.method='recording' AND r.kind='external_priest'
 AND report.author_id=public.ctm_actor_id() AND data->>'captured_by_id'=public.ctm_actor_id()::text
 AND public.ctm_case_writer(c.id) AND c.status='open' AND p.status='open'
 AND r.id=public.ctm_context_uuid('ctm.recording_request') AND f.id=public.ctm_context_uuid('ctm.recording_file')
 AND report.completion_date::text=current_setting('ctm.recording_date',true)
 AND current_setting('ctm.recording_acknowledged',true)='true'
 AND data->'notice_recorded'='true'::jsonb AND data->'recording_notice'->'acknowledged'='true'::jsonb
 AND data->>'appointment_id' IS NULL AND (operation<>'insert' OR data->>'finalized_at' IS NULL)
 AND revision.actor_id=public.ctm_actor_id() AND revision.answers=jsonb_build_object('files',jsonb_build_array(f.id::text))
 AND coalesce(revision.observations,'')='' AND a.case_id=c.id AND a.proceeding_id=p.id
 AND a.owner_id IS NULL AND a.application_id IS NULL AND a.report_request_id IS NULL
 AND a.visibility='council' AND a.category='AUDIO' AND (f.mime_type LIKE 'audio/%%' OR f.mime_type LIKE 'video/%%')
 AND NOT EXISTS(SELECT 1 FROM public.tribunal_fileversion newer WHERE newer.attachment_id=a.id AND newer.number>f.number)
 AND (SELECT e.result FROM public.tribunal_filetechnicalevent e WHERE e.file_id=f.id AND e.task='scan'
 ORDER BY e.created_at DESC,e.id DESC LIMIT 1)='clean')
$$;
REVOKE ALL ON FUNCTION public.ctm_recording_capture_allowed(jsonb,text) FROM PUBLIC;

CREATE OR REPLACE FUNCTION public.ctm_report_root_writable(data jsonb) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
 SELECT EXISTS(SELECT 1 FROM public.tribunal_reportrequest r JOIN public.tribunal_party s ON s.id=r.subject_id
  JOIN public.tribunal_proceeding p ON p.id=r.proceeding_id JOIN public.tribunal_case c ON c.id=r.case_id
  WHERE r.id=(data->>'request_id')::uuid AND p.status='open' AND c.status='open' AND r.sent_at IS NOT NULL
  AND ((data->>'method'<>'recording' AND r.state IN ('sent','completed') AND r.kind<>'external_priest' AND data->>'author_id'=public.ctm_actor_id()::text
    AND ((public.ctm_actor_role()='applicant' AND s.account_id=public.ctm_actor_id() AND r.kind<>'interview') OR public.ctm_case_writer(r.case_id))
    AND (r.kind NOT IN ('medical','psychological') OR EXISTS(SELECT 1 FROM public.tribunal_medicalrelease release
       WHERE release.request_id=r.id AND release.subject_id=s.account_id AND release.scope->'council'='true'::jsonb))) OR
   (data->>'author_id'=public.ctm_actor_id()::text AND data->>'method'='paper' AND r.kind='external_priest'
      AND data->>'completion_date'=current_setting('ctm.paper_date',true)
      AND public.ctm_paper_file_allowed(r.id,public.ctm_context_uuid('ctm.paper_file'))) OR
   (data->>'author_id'=public.ctm_actor_id()::text AND data->>'method'='recording'
      AND data->>'completion_date'=current_setting('ctm.recording_date',true)
      AND public.ctm_recording_file_allowed(r.id,public.ctm_context_uuid('ctm.recording_file'))) OR
   (data->>'author_id' IS NULL AND data->>'method'='external' AND r.state='sent'
      AND r.id::text=current_setting('ctm.external_request',true) AND public.ctm_external_context_valid(false))))
$$;

CREATE OR REPLACE FUNCTION public.ctm_request_source_writable(resource text,data jsonb) RETURNS boolean
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
BEGIN
 IF resource='fileversion' THEN
  RETURN EXISTS(SELECT 1 FROM public.tribunal_attachment a WHERE a.id=(data->>'attachment_id')::uuid
    AND public.ctm_request_source_writable('attachment',to_jsonb(a)));
 END IF;
 IF resource='attachment' THEN
  IF data->>'report_request_id' IS NULL THEN RETURN true; END IF;
  RETURN EXISTS(SELECT 1 FROM public.tribunal_reportrequest r JOIN public.tribunal_party s ON s.id=r.subject_id
    JOIN public.tribunal_proceeding p ON p.id=r.proceeding_id JOIN public.tribunal_case c ON c.id=r.case_id
    WHERE r.id=(data->>'report_request_id')::uuid AND r.state='sent' AND r.sent_at IS NOT NULL
     AND p.status='open' AND c.status='open' AND r.case_id=(data->>'case_id')::uuid AND p.id=(data->>'proceeding_id')::uuid
     AND ((r.kind IN ('external_priest','interview') AND data->>'owner_id' IS NULL
       AND data->>'application_id' IS NULL AND data->>'visibility'='council' AND public.ctm_case_writer(c.id))
      OR (r.kind NOT IN ('external_priest','interview') AND s.account_id::text=data->>'owner_id'
       AND (public.ctm_case_writer(c.id) OR (public.ctm_actor_role()='applicant' AND s.account_id=public.ctm_actor_id()))
       AND data->>'visibility'=CASE WHEN r.kind IN ('medical','psychological') THEN 'medical' ELSE 'own' END))
     AND (data->>'category'<>'CONSENT' OR (r.kind IN ('medical','psychological') AND NOT EXISTS(
        SELECT 1 FROM public.tribunal_medicalrelease release WHERE release.request_id=r.id))));
 END IF;
 IF resource='medicalrelease' THEN
  RETURN public.ctm_actor_role()='applicant' AND data->>'subject_id'=public.ctm_actor_id()::text
   AND data->'scope'->'council'='true'::jsonb AND EXISTS(
    SELECT 1 FROM public.tribunal_reportrequest r JOIN public.tribunal_party s ON s.id=r.subject_id
    JOIN public.tribunal_proceeding p ON p.id=r.proceeding_id JOIN public.tribunal_case c ON c.id=r.case_id
    JOIN public.tribunal_fileversion f ON f.id=(data->>'signature_id')::uuid
    JOIN public.tribunal_attachment a ON a.id=f.attachment_id
    JOIN public.tribunal_questionnaireversion d ON d.id=(data->>'declaration_id')::uuid
    WHERE r.id=(data->>'request_id')::uuid AND r.kind IN ('medical','psychological') AND r.state='sent' AND r.sent_at IS NOT NULL
     AND s.account_id=public.ctm_actor_id() AND p.status='open' AND c.status='open'
     AND a.report_request_id=r.id AND a.owner_id=s.account_id AND a.case_id=r.case_id AND a.proceeding_id=r.proceeding_id
     AND a.category='CONSENT' AND a.visibility='medical' AND f.mime_type IN ('application/pdf','image/png','image/jpeg')
     AND NOT EXISTS(SELECT 1 FROM public.tribunal_fileversion newer WHERE newer.attachment_id=a.id AND newer.number>f.number)
     AND (SELECT e.result FROM public.tribunal_filetechnicalevent e WHERE e.file_id=f.id AND e.task='scan' ORDER BY e.created_at DESC,e.id DESC LIMIT 1)='clean'
     AND d.purpose='medical_release' AND d.published AND btrim(d.declaration_en)<>'' AND btrim(d.declaration_ar)<>''
     AND NOT EXISTS(SELECT 1 FROM public.tribunal_questionnaireversion newer WHERE newer.purpose=d.purpose AND newer.published AND newer.number>d.number)
     AND NOT EXISTS(SELECT 1 FROM public.tribunal_medicalrelease old WHERE old.request_id=r.id)
     AND data->'scope'->>'purpose'=r.kind AND data->'scope'->>'request_id'=r.id::text
     AND data->'scope'->>'proceeding_id'=p.id::text);
 END IF;
 IF resource='reportrevision' AND EXISTS(SELECT 1 FROM public.tribunal_report report
   WHERE report.id=(data->>'report_id')::uuid AND report.method='paper') THEN
  RETURN EXISTS(SELECT 1 FROM public.tribunal_report report
   WHERE report.id=(data->>'report_id')::uuid AND report.author_id=public.ctm_actor_id()
   AND data->>'actor_id'=public.ctm_actor_id()::text AND (data->>'number')::int=1
   AND coalesce(data->>'observations','')='' AND report.completion_date::text=current_setting('ctm.paper_date',true)
   AND data->'answers'=jsonb_build_object('files',jsonb_build_array(current_setting('ctm.paper_file',true)))
   AND public.ctm_paper_file_allowed(report.request_id,public.ctm_context_uuid('ctm.paper_file')));
 END IF;
 IF resource='reportrevision' AND EXISTS(SELECT 1 FROM public.tribunal_report report
   WHERE report.id=(data->>'report_id')::uuid AND report.method='recording') THEN
  RETURN EXISTS(SELECT 1 FROM public.tribunal_report report WHERE report.id=(data->>'report_id')::uuid
   AND report.author_id=public.ctm_actor_id() AND data->>'actor_id'=public.ctm_actor_id()::text
   AND (data->>'number')::int=1 AND coalesce(data->>'observations','')=''
   AND report.completion_date::text=current_setting('ctm.recording_date',true)
   AND data->'answers'=jsonb_build_object('files',jsonb_build_array(current_setting('ctm.recording_file',true)))
   AND public.ctm_recording_file_allowed(report.request_id,public.ctm_context_uuid('ctm.recording_file')));
 END IF;
 IF resource='reportrevision' THEN
  RETURN EXISTS(SELECT 1 FROM public.tribunal_report report JOIN public.tribunal_reportrequest r ON r.id=report.request_id
   JOIN public.tribunal_proceeding p ON p.id=r.proceeding_id JOIN public.tribunal_case c ON c.id=r.case_id
   WHERE report.id=(data->>'report_id')::uuid AND p.status='open' AND c.status='open'
   AND ((public.ctm_actor_role()='applicant' AND report.author_id=public.ctm_actor_id()
     AND r.state='sent' AND (data->>'number')::int=1 AND coalesce(data->>'observations','')='')
    OR (public.ctm_case_writer(r.case_id) AND report.author_id=public.ctm_actor_id())
    OR (report.author_id IS NULL AND (data->>'number')::int=1 AND r.state='sent' AND public.ctm_external_context_valid(false)
      AND r.id::text=current_setting('ctm.external_request',true))));
 END IF;
 RETURN false;
END $$;

CREATE OR REPLACE FUNCTION public.ctm_external_status_receipt() RETURNS jsonb
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
 SELECT jsonb_build_object(
 'state', CASE WHEN r.expires_at<=statement_timestamp() THEN 'expired'
   WHEN r.state='completed' AND report.id IS NOT NULL THEN 'completed'
   WHEN r.state='cancelled' THEN 'cancelled'
   WHEN r.state='closed' OR c.status<>'open' OR p.status<>'open' THEN 'closed'
   WHEN r.state='sent' THEN 'active' ELSE 'unavailable' END,
 'expires_at',r.expires_at,
 'receipt',CASE WHEN r.state='completed' AND report.id IS NOT NULL AND r.expires_at>statement_timestamp()
   THEN jsonb_build_object('report_id',report.id,'completed_at',report.created_at) ELSE NULL END)
 FROM public.tribunal_reportrequest r
 JOIN public.tribunal_proceeding p ON p.id=r.proceeding_id AND p.case_id=r.case_id
 JOIN public.tribunal_case c ON c.id=r.case_id
 LEFT JOIN public.tribunal_report report ON report.request_id=r.id AND ((report.method='external' AND report.author_id IS NULL) OR report.method IN ('paper','recording'))
 WHERE r.id=public.ctm_context_uuid('ctm.external_request') AND r.kind='external_priest'
 AND length(r.token_hash)=64 AND r.token_hash=current_setting('ctm.external_digest',true)
 AND r.expires_at IS NOT NULL
$$;
REVOKE ALL ON FUNCTION public.ctm_external_status_receipt() FROM PUBLIC;

CREATE OR REPLACE FUNCTION public.ctm_media_writable(resource text,data jsonb,operation text) RETURNS boolean
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
BEGIN
 IF resource='recording' THEN
  IF operation='lock' THEN RETURN public.ctm_media_reviewer((data->>'id')::uuid); END IF;
  IF EXISTS(SELECT 1 FROM public.tribunal_report report WHERE report.id=(data->>'report_id')::uuid AND report.method='recording') THEN
   RETURN public.ctm_recording_capture_allowed(data,operation);
  END IF;
  RETURN (operation<>'insert' OR data->>'finalized_at' IS NULL) AND EXISTS(
   SELECT 1 FROM public.tribunal_fileversion f JOIN public.tribunal_attachment a ON a.id=f.attachment_id
    JOIN public.tribunal_case c ON c.id=a.case_id LEFT JOIN public.tribunal_report report ON report.id=(data->>'report_id')::uuid
    LEFT JOIN public.tribunal_reportrequest r ON r.id=report.request_id
   WHERE f.id=(data->>'file_id')::uuid AND a.visibility='council' AND public.ctm_case_writer(c.id)
    AND (f.mime_type LIKE 'audio/%%' OR f.mime_type LIKE 'video/%%')
    AND (r.id IS NULL OR (r.kind NOT IN ('medical','psychological') AND r.case_id=c.id AND r.proceeding_id=a.proceeding_id))
    AND ((data->>'report_id' IS NOT NULL) OR public.ctm_actor_role() IN ('admin','secretary')));
 END IF;
 IF resource='processingrun' THEN
  RETURN data->>'state'='queued' AND data->>'purpose'='transcription' AND coalesce(data->>'engine','')=''
   AND coalesce(data->>'error','')='' AND EXISTS(SELECT 1 FROM public.tribunal_recording x
    JOIN public.tribunal_fileversion f ON f.id=x.file_id JOIN public.tribunal_attachment a ON a.id=f.attachment_id
    JOIN public.tribunal_case c ON c.id=a.case_id WHERE x.file_id=(data->>'file_id')::uuid
     AND c.status='open' AND public.ctm_media_safe(x.id) AND public.ctm_media_reviewer(x.id)
     AND (data->>'attempt')::int=coalesce((SELECT max(old.attempt)+1 FROM public.tribunal_processingrun old
       WHERE old.file_id=x.file_id AND old.purpose='transcription'),1)
     AND NOT EXISTS(SELECT 1 FROM public.tribunal_processingrun active WHERE active.file_id=x.file_id
       AND active.purpose='transcription' AND active.state IN ('queued','running')));
 END IF;
 IF resource='transcriptreview' THEN
  RETURN data->>'actor_id'=public.ctm_actor_id()::text AND EXISTS(SELECT 1 FROM public.tribunal_transcriptrevision r
    JOIN public.tribunal_processingrun run ON run.id=r.run_id WHERE r.id=(data->>'revision_id')::uuid
     AND run.state='completed' AND public.ctm_media_safe(r.recording_id) AND public.ctm_media_reviewer(r.recording_id)
     AND NOT EXISTS(SELECT 1 FROM public.tribunal_transcriptrevision newer WHERE newer.recording_id=r.recording_id
       AND newer.kind=r.kind AND newer.language=r.language AND newer.number>r.number));
 END IF;

 IF resource='transcriptrevision' THEN
  RETURN data->>'actor_id'=public.ctm_actor_id()::text AND EXISTS(
   SELECT 1 FROM public.tribunal_transcriptrevision prior JOIN public.tribunal_processingrun run ON run.id=prior.run_id
   WHERE prior.recording_id=(data->>'recording_id')::uuid AND prior.run_id=(data->>'run_id')::uuid
    AND prior.kind=data->>'kind' AND prior.language=data->>'language' AND run.state='completed'
    AND public.ctm_media_safe(prior.recording_id) AND public.ctm_media_reviewer(prior.recording_id)
    AND (data->>'number')::int=(SELECT max(v.number)+1 FROM public.tribunal_transcriptrevision v
       WHERE v.recording_id=prior.recording_id AND v.kind=prior.kind AND v.language=prior.language));
 END IF;
 RETURN false; -- provider output requires a separate reviewed worker scope; never app impersonation
END $$;
