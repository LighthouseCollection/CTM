CREATE FUNCTION public.ctm_media_recording_visible(target uuid) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
 SELECT public.ctm_is_council() AND EXISTS(SELECT 1 FROM public.tribunal_recording x
  JOIN public.tribunal_fileversion f ON f.id=x.file_id JOIN public.tribunal_attachment a ON a.id=f.attachment_id
  LEFT JOIN public.tribunal_report report ON report.id=x.report_id LEFT JOIN public.tribunal_reportrequest r ON r.id=report.request_id
  WHERE x.id=target AND a.visibility='council' AND a.report_request_id IS NULL AND a.application_id IS NULL
   AND (x.report_id IS NULL OR (r.kind NOT IN ('medical','psychological') AND r.case_id=a.case_id AND r.proceeding_id=a.proceeding_id)))
$$;

CREATE FUNCTION public.ctm_media_reviewer(target uuid) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
 SELECT public.ctm_media_recording_visible(target) AND EXISTS(SELECT 1 FROM public.tribunal_recording x
  JOIN public.tribunal_fileversion f ON f.id=x.file_id JOIN public.tribunal_attachment a ON a.id=f.attachment_id
  JOIN public.tribunal_case c ON c.id=a.case_id WHERE x.id=target AND
   (public.ctm_actor_role() IN ('admin','secretary') OR (x.report_id IS NOT NULL AND c.assigned_member_id=public.ctm_actor_id())))
$$;

CREATE FUNCTION public.ctm_media_safe(target uuid) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
 SELECT public.ctm_media_recording_visible(target) AND EXISTS(SELECT 1 FROM public.tribunal_recording x WHERE x.id=target
   AND x.finalized_at IS NOT NULL AND x.notice_recorded AND
    (SELECT e.result FROM public.tribunal_filetechnicalevent e WHERE e.file_id=x.file_id AND e.task='scan' ORDER BY e.created_at DESC,e.id DESC LIMIT 1)='clean')
$$;

CREATE FUNCTION public.ctm_media_readable(resource text,data jsonb) RETURNS boolean
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
DECLARE target uuid;
BEGIN
 CASE resource
 WHEN 'recording' THEN RETURN public.ctm_media_recording_visible((data->>'id')::uuid);
 WHEN 'processingrun' THEN RETURN EXISTS(SELECT 1 FROM public.tribunal_recording x WHERE x.file_id=(data->>'file_id')::uuid AND public.ctm_media_recording_visible(x.id));
 WHEN 'transcriptrevision' THEN target=(data->>'id')::uuid;
 WHEN 'transcriptreview' THEN target=(data->>'revision_id')::uuid;
 ELSE RETURN false;
 END CASE;
 RETURN EXISTS(SELECT 1 FROM public.tribunal_transcriptrevision revision JOIN public.tribunal_recording x ON x.id=revision.recording_id
   JOIN public.tribunal_processingrun run ON run.id=revision.run_id WHERE revision.id=target AND run.file_id=x.file_id
    AND run.purpose='transcription' AND run.state='completed' AND public.ctm_media_safe(x.id)
    AND (public.ctm_media_reviewer(x.id) OR EXISTS(SELECT 1 FROM public.tribunal_transcriptreview review WHERE review.revision_id=revision.id)));
END $$;

CREATE FUNCTION public.ctm_media_writable(resource text,data jsonb,operation text) RETURNS boolean
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
BEGIN
 IF resource='recording' THEN
  IF operation='lock' THEN RETURN public.ctm_media_reviewer((data->>'id')::uuid); END IF;
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
 RETURN false; -- provider output requires a separate reviewed worker scope; never app impersonation
END $$;

CREATE FUNCTION public.ctm_guard_media_history() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public AS $$
BEGIN
 IF TG_TABLE_NAME='tribunal_processingrun' THEN
  IF TG_OP='UPDATE' AND (NEW.file_id,NEW.purpose,NEW.attempt) IS DISTINCT FROM (OLD.file_id,OLD.purpose,OLD.attempt) THEN
   RAISE EXCEPTION 'Processing attempt identity is retained' USING ERRCODE='42501';
  END IF;
  IF NEW.attempt<1 THEN RAISE EXCEPTION 'Positive attempt required' USING ERRCODE='23514'; END IF;
  RETURN NEW;
 END IF;
 IF TG_TABLE_NAME='tribunal_transcriptrevision' THEN
  IF NOT EXISTS(SELECT 1 FROM public.tribunal_recording x JOIN public.tribunal_processingrun run ON run.file_id=x.file_id
    WHERE x.id=NEW.recording_id AND run.id=NEW.run_id AND run.purpose='transcription' AND x.finalized_at IS NOT NULL) THEN
   RAISE EXCEPTION 'Transcript output must match finalized recording and attempt' USING ERRCODE='42501';
  END IF;
  RETURN NEW;
 END IF;
 RETURN NEW;
END $$;
