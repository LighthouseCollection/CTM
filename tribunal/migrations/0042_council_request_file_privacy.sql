CREATE OR REPLACE FUNCTION public.ctm_attachment_visible(target uuid) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
 SELECT coalesce(EXISTS(SELECT 1 FROM public.tribunal_attachment f
   LEFT JOIN public.tribunal_application a ON a.id=f.application_id
   WHERE f.id=target AND public.ctm_actor_role() IS NOT NULL
   AND (public.ctm_is_council() OR NOT EXISTS(SELECT 1 FROM public.tribunal_reportrequest request
     WHERE request.id=f.report_request_id AND request.kind IN ('external_priest','interview'))) AND (
     (f.owner_id=public.ctm_actor_id() AND f.visibility<>'council') OR
     (public.ctm_is_council() AND (f.application_id IS NULL OR a.submitted_at IS NOT NULL)
       AND (f.visibility<>'medical' OR EXISTS(SELECT 1 FROM public.tribunal_medicalrelease r WHERE r.request_id=f.report_request_id AND r.subject_id=f.owner_id AND r.scope->'council'='true'::jsonb))) OR
     EXISTS(SELECT 1 FROM public.tribunal_fileversion v WHERE v.attachment_id=f.id AND public.ctm_decree_released(v.id))
   )),false)
$$;

CREATE OR REPLACE FUNCTION public.ctm_file_row_readable(attachment_id uuid,file_id uuid,version_number integer) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
 SELECT EXISTS(SELECT 1 FROM public.tribunal_attachment a WHERE a.id=attachment_id
   AND public.ctm_actor_role() IS NOT NULL
   AND (public.ctm_is_council() OR NOT EXISTS(SELECT 1 FROM public.tribunal_reportrequest request
     WHERE request.id=a.report_request_id AND request.kind IN ('external_priest','interview'))) AND (
      (public.ctm_is_council() AND public.ctm_attachment_visible(a.id) AND public.ctm_filing_source_formal('fileversion',file_id)) OR
      public.ctm_decree_released(file_id) OR
      (a.owner_id=public.ctm_actor_id() AND a.visibility<>'council' AND NOT EXISTS(
         SELECT 1 FROM public.tribunal_fileversion v WHERE v.attachment_id=a.id AND v.number>version_number))))
$$;

CREATE OR REPLACE FUNCTION public.ctm_attachment_writable(data jsonb) RETURNS boolean
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
DECLARE actor uuid=public.ctm_actor_id(); target_case uuid=(data->>'case_id')::uuid;
BEGIN
 IF public.ctm_actor_role() IS NULL THEN RETURN false; END IF;
 IF EXISTS(SELECT 1 FROM public.tribunal_reportrequest r
   WHERE r.id=(data->>'report_request_id')::uuid AND r.kind IN ('external_priest','interview')) THEN
  RETURN data->>'owner_id' IS NULL AND data->>'visibility'='council' AND data->>'application_id' IS NULL
   AND EXISTS(SELECT 1 FROM public.tribunal_reportrequest r JOIN public.tribunal_proceeding p ON p.id=r.proceeding_id
     WHERE r.id=(data->>'report_request_id')::uuid AND r.case_id=target_case
      AND r.proceeding_id=(data->>'proceeding_id')::uuid AND r.state='sent' AND p.status='open'
      AND public.ctm_case_writer(r.case_id));
 END IF;
 IF data->>'application_id' IS NOT NULL THEN
   RETURN EXISTS(SELECT 1 FROM public.tribunal_application a WHERE a.id=(data->>'application_id')::uuid
      AND a.owner_id::text=data->>'owner_id' AND a.case_id IS NOT DISTINCT FROM target_case
      AND a.proceeding_id IS NOT DISTINCT FROM (data->>'proceeding_id')::uuid
      AND (a.owner_id=actor OR (a.submitted_at IS NOT NULL AND public.ctm_case_writer(a.case_id))));
 ELSIF data->>'report_request_id' IS NOT NULL THEN
   RETURN EXISTS(SELECT 1 FROM public.tribunal_reportrequest r JOIN public.tribunal_party p ON p.id=r.subject_id
      WHERE r.id=(data->>'report_request_id')::uuid AND r.case_id=target_case AND r.proceeding_id=(data->>'proceeding_id')::uuid
      AND p.account_id::text=data->>'owner_id' AND r.state='sent'
      AND (p.account_id=actor OR public.ctm_case_writer(r.case_id)));
 ELSE
   RETURN public.ctm_case_writer(target_case) AND data->>'visibility' IN ('council','medical')
      AND EXISTS(SELECT 1 FROM public.tribunal_proceeding p WHERE p.id=(data->>'proceeding_id')::uuid AND p.case_id=target_case AND p.status='open');
 END IF;
END $$;

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
