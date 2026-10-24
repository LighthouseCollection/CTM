CREATE FUNCTION public.ctm_paper_file_allowed(target uuid,source uuid) RETURNS boolean
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
BEGIN
 RETURN coalesce(target=public.ctm_context_uuid('ctm.paper_request') AND source=public.ctm_context_uuid('ctm.paper_file')
 AND nullif(current_setting('ctm.paper_date',true),'')::date<=(statement_timestamp() AT TIME ZONE 'America/Los_Angeles')::date AND EXISTS(
 SELECT 1 FROM public.tribunal_reportrequest r JOIN public.tribunal_proceeding p ON p.id=r.proceeding_id
 JOIN public.tribunal_case c ON c.id=r.case_id JOIN public.tribunal_attachment a ON a.report_request_id=r.id
 JOIN public.tribunal_fileversion f ON f.attachment_id=a.id
 WHERE r.id=target AND f.id=source AND r.kind='external_priest' AND r.state='sent' AND r.sent_at IS NOT NULL
 AND p.case_id=c.id AND c.status='open' AND p.status='open' AND public.ctm_case_writer(c.id)
 AND a.case_id=c.id AND a.proceeding_id=p.id AND a.application_id IS NULL AND a.owner_id IS NULL
 AND a.visibility='council' AND a.category='REPORT' AND f.mime_type='application/pdf'
 AND NOT EXISTS(SELECT 1 FROM public.tribunal_fileversion newer WHERE newer.attachment_id=a.id AND newer.number>f.number)
 AND (SELECT e.result FROM public.tribunal_filetechnicalevent e WHERE e.file_id=f.id AND e.task='scan'
 ORDER BY e.created_at DESC,e.id DESC LIMIT 1)='clean'),false);
EXCEPTION WHEN invalid_datetime_format OR datetime_field_overflow THEN RETURN false;
END $$;
REVOKE ALL ON FUNCTION public.ctm_paper_file_allowed(uuid,uuid) FROM PUBLIC;

CREATE OR REPLACE FUNCTION public.ctm_report_root_writable(data jsonb) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
 SELECT EXISTS(SELECT 1 FROM public.tribunal_reportrequest r JOIN public.tribunal_party s ON s.id=r.subject_id
  JOIN public.tribunal_proceeding p ON p.id=r.proceeding_id JOIN public.tribunal_case c ON c.id=r.case_id
  WHERE r.id=(data->>'request_id')::uuid AND p.status='open' AND c.status='open' AND r.sent_at IS NOT NULL
  AND ((r.state IN ('sent','completed') AND r.kind<>'external_priest' AND data->>'author_id'=public.ctm_actor_id()::text
    AND ((public.ctm_actor_role()='applicant' AND s.account_id=public.ctm_actor_id() AND r.kind<>'interview') OR public.ctm_case_writer(r.case_id))
    AND (r.kind NOT IN ('medical','psychological') OR EXISTS(SELECT 1 FROM public.tribunal_medicalrelease release
       WHERE release.request_id=r.id AND release.subject_id=s.account_id AND release.scope->'council'='true'::jsonb))) OR
   (data->>'author_id'=public.ctm_actor_id()::text AND data->>'method'='paper' AND r.kind='external_priest'
      AND data->>'completion_date'=current_setting('ctm.paper_date',true)
      AND public.ctm_paper_file_allowed(r.id,public.ctm_context_uuid('ctm.paper_file'))) OR
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
 LEFT JOIN public.tribunal_report report ON report.request_id=r.id AND ((report.method='external' AND report.author_id IS NULL) OR report.method='paper')
 WHERE r.id=public.ctm_context_uuid('ctm.external_request') AND r.kind='external_priest'
 AND length(r.token_hash)=64 AND r.token_hash=current_setting('ctm.external_digest',true)
 AND r.expires_at IS NOT NULL
$$;
REVOKE ALL ON FUNCTION public.ctm_external_status_receipt() FROM PUBLIC;
