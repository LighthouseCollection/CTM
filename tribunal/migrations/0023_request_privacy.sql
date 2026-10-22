CREATE FUNCTION public.ctm_request_readable(data jsonb) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
 SELECT coalesce(public.ctm_is_council() OR
   (public.ctm_actor_role()='applicant' AND data->>'sent_at' IS NOT NULL
    AND data->>'kind' NOT IN ('interview','external_priest') AND EXISTS(
      SELECT 1 FROM public.tribunal_party s WHERE s.id=(data->>'subject_id')::uuid AND s.account_id=public.ctm_actor_id())) OR
   (data->>'id'=current_setting('ctm.external_request',true) AND public.ctm_external_context_valid(true)),false)
$$;

CREATE FUNCTION public.ctm_request_writable(data jsonb, operation text) RETURNS boolean
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
DECLARE actor uuid=public.ctm_actor_id(); writer boolean;
BEGIN
 writer=public.ctm_case_writer((data->>'case_id')::uuid);
 IF operation='insert' THEN
  RETURN coalesce(writer AND data->>'author_id'=actor::text AND data->>'state'='draft' AND data->>'sent_at' IS NULL
   AND EXISTS(SELECT 1 FROM public.tribunal_proceeding p JOIN public.tribunal_case c ON c.id=p.case_id
    JOIN public.tribunal_party s ON s.case_id=c.id WHERE p.id=(data->>'proceeding_id')::uuid
    AND c.id=(data->>'case_id')::uuid AND s.id=(data->>'subject_id')::uuid AND p.status='open' AND c.status='open'),false);
 END IF;
 IF writer THEN RETURN true; END IF;
 IF EXISTS(SELECT 1 FROM public.tribunal_case c JOIN public.tribunal_proceeding p ON p.case_id=c.id
    WHERE c.id=(data->>'case_id')::uuid AND p.id=(data->>'proceeding_id')::uuid
    AND c.status='closed' AND p.status='closed' AND (public.ctm_actor_role() IN ('admin','secretary')
       OR (public.ctm_is_council() AND c.assigned_member_id=actor))) THEN
  RETURN (operation='lock' AND data->>'state' IN ('draft','sent')) OR
    (operation='update' AND data->>'state' IN ('closed','cancelled'));
 END IF;
 IF data->>'id'=current_setting('ctm.external_request',true) AND public.ctm_external_context_valid(true) THEN
  RETURN operation='lock' OR data->>'state'='sent' OR (data->>'state'='completed' AND EXISTS(SELECT 1 FROM public.tribunal_report r
    WHERE r.request_id=(data->>'id')::uuid AND r.author_id IS NULL AND r.method='external'));
 END IF;
 IF public.ctm_actor_role()='applicant' AND data->>'sent_at' IS NOT NULL
    AND data->>'kind' NOT IN ('interview','external_priest') AND data->>'state' IN ('sent','completed')
    AND EXISTS(SELECT 1 FROM public.tribunal_party s WHERE s.id=(data->>'subject_id')::uuid AND s.account_id=actor) THEN
  RETURN operation='lock' OR (data->>'state'='completed' AND EXISTS(SELECT 1 FROM public.tribunal_report r
    WHERE r.request_id=(data->>'id')::uuid AND r.author_id=actor));
 END IF;
 RETURN false;
END $$;

CREATE FUNCTION public.ctm_report_root_readable(data jsonb) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
 SELECT coalesce(public.ctm_is_council() OR EXISTS(SELECT 1 FROM public.tribunal_reportrequest r
  JOIN public.tribunal_party s ON s.id=r.subject_id WHERE r.id=(data->>'request_id')::uuid
  AND r.sent_at IS NOT NULL AND r.kind NOT IN ('interview','external_priest') AND s.account_id=public.ctm_actor_id()
  AND data->>'author_id'=public.ctm_actor_id()::text AND public.ctm_actor_role()='applicant') OR
  (data->>'request_id'=current_setting('ctm.external_request',true) AND public.ctm_external_context_valid(true)),false)
$$;

CREATE FUNCTION public.ctm_report_root_writable(data jsonb) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
 SELECT EXISTS(SELECT 1 FROM public.tribunal_reportrequest r JOIN public.tribunal_party s ON s.id=r.subject_id
  JOIN public.tribunal_proceeding p ON p.id=r.proceeding_id JOIN public.tribunal_case c ON c.id=r.case_id
  WHERE r.id=(data->>'request_id')::uuid AND p.status='open' AND c.status='open' AND r.sent_at IS NOT NULL
  AND ((r.state IN ('sent','completed') AND r.kind<>'external_priest' AND data->>'author_id'=public.ctm_actor_id()::text
    AND ((public.ctm_actor_role()='applicant' AND s.account_id=public.ctm_actor_id() AND r.kind<>'interview') OR public.ctm_case_writer(r.case_id))
    AND (r.kind NOT IN ('medical','psychological') OR EXISTS(SELECT 1 FROM public.tribunal_medicalrelease release
       WHERE release.request_id=r.id AND release.subject_id=s.account_id AND release.scope->'council'='true'::jsonb))) OR
   (data->>'author_id' IS NULL AND data->>'method'='external' AND r.state='sent'
      AND r.id::text=current_setting('ctm.external_request',true) AND public.ctm_external_context_valid(false))))
$$;

CREATE FUNCTION public.ctm_request_source_writable(resource text,data jsonb) RETURNS boolean
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
     AND s.account_id::text=data->>'owner_id' AND (public.ctm_case_writer(c.id) OR
       (public.ctm_actor_role()='applicant' AND s.account_id=public.ctm_actor_id() AND r.kind NOT IN ('interview','external_priest')))
     AND data->>'visibility'=CASE WHEN r.kind IN ('medical','psychological') THEN 'medical' ELSE 'own' END
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

CREATE FUNCTION public.ctm_guard_sent_request() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public AS $$
BEGIN
 IF TG_TABLE_NAME='tribunal_attachment' THEN
  IF OLD.report_request_id IS NOT NULL AND
    (NEW.case_id,NEW.proceeding_id,NEW.category,NEW.context,NEW.visibility) IS DISTINCT FROM
    (OLD.case_id,OLD.proceeding_id,OLD.category,OLD.context,OLD.visibility) THEN
   RAISE EXCEPTION 'Request file purpose and scope are retained' USING ERRCODE='42501';
  END IF;
  RETURN NEW;
 END IF;
 IF TG_TABLE_NAME='tribunal_report' THEN
  IF (NEW.author_id,NEW.method,NEW.completion_date) IS DISTINCT FROM (OLD.author_id,OLD.method,OLD.completion_date) THEN
   RAISE EXCEPTION 'Report source author, method and completion date are retained' USING ERRCODE='42501';
  END IF;
  RETURN NEW;
 END IF;
 IF OLD.sent_at IS NOT NULL AND (NEW.questions,NEW.instructions,NEW.language,NEW.title,NEW.sent_at)
    IS DISTINCT FROM (OLD.questions,OLD.instructions,OLD.language,OLD.title,OLD.sent_at) THEN
  RAISE EXCEPTION 'Sent request content is frozen' USING ERRCODE='42501';
 END IF;
 IF OLD.state IN ('completed','cancelled','closed') AND NEW.state IS DISTINCT FROM OLD.state THEN
  RAISE EXCEPTION 'Terminal request cannot be reopened' USING ERRCODE='42501';
 END IF;
 IF OLD.sent_at IS NOT NULL AND NEW.state='draft' THEN
  RAISE EXCEPTION 'Sent request cannot return to draft' USING ERRCODE='42501';
 END IF;
 IF public.ctm_actor_role()='applicant' AND (to_jsonb(NEW)-'state') IS DISTINCT FROM (to_jsonb(OLD)-'state') THEN
  RAISE EXCEPTION 'Recipient can only complete the bound request' USING ERRCODE='42501';
 END IF;
 IF public.ctm_actor_id() IS NULL AND OLD.id::text=current_setting('ctm.external_request',true)
   AND (to_jsonb(NEW)-ARRAY['state','saved_response']) IS DISTINCT FROM (to_jsonb(OLD)-ARRAY['state','saved_response']) THEN
  RAISE EXCEPTION 'External capability is response-only' USING ERRCODE='42501';
 END IF;
 RETURN NEW;
END $$;
