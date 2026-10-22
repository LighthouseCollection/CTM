-- Original history determines private edit windows; no mutable privacy flag or backfill.
CREATE FUNCTION public.ctm_filing_source_formal(resource text, target uuid) RETURNS boolean
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
DECLARE app_id uuid; saved_at timestamptz; app_state text; formal boolean; returned_at timestamptz;
BEGIN
 IF resource='answerrevision' THEN
  SELECT r.application_id,r.created_at INTO app_id,saved_at FROM public.tribunal_answerrevision r WHERE r.id=target;
  SELECT EXISTS(SELECT 1 FROM public.tribunal_submission s WHERE s.revision_id=target) INTO formal;
 ELSIF resource='fileversion' THEN
  SELECT a.application_id,v.created_at INTO app_id,saved_at FROM public.tribunal_fileversion v JOIN public.tribunal_attachment a ON a.id=v.attachment_id JOIN public.tribunal_application p ON p.id=a.application_id WHERE v.id=target AND a.owner_id=p.owner_id AND a.report_request_id IS NULL;
  IF app_id IS NULL THEN RETURN true; END IF;
  SELECT EXISTS(SELECT 1 FROM public.tribunal_submission s CROSS JOIN LATERAL jsonb_array_elements(s.manifest) item WHERE s.application_id=app_id AND item->>'id'=target::text) INTO formal;
 ELSE RETURN false;
 END IF;
 IF app_id IS NULL THEN RETURN false; END IF;
 SELECT status INTO app_state FROM public.tribunal_application WHERE id=app_id;
 IF formal THEN RETURN true; END IF;
 IF app_state='returned' THEN RETURN false; END IF;
 SELECT max(r.created_at) INTO returned_at FROM public.tribunal_completenessreview r JOIN public.tribunal_submission s ON s.id=r.submission_id WHERE s.application_id=app_id AND r.result='reject' AND r.created_at<=saved_at;
 RETURN returned_at IS NULL OR EXISTS(SELECT 1 FROM public.tribunal_submission s WHERE s.application_id=app_id AND s.created_at>returned_at AND s.created_at<=saved_at);
END
$$;

CREATE FUNCTION public.ctm_correction_notice_visible(notice_key text) RETURNS boolean
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
DECLARE kind text; source_id uuid;
BEGIN
 kind=split_part(notice_key,':',1);
 IF kind NOT IN ('answer_changed','file_uploaded') THEN RETURN true; END IF;
 BEGIN source_id=split_part(notice_key,':',2)::uuid; EXCEPTION WHEN invalid_text_representation THEN RETURN false; END;
 RETURN public.ctm_filing_source_formal(CASE WHEN kind='answer_changed' THEN 'answerrevision' ELSE 'fileversion' END,source_id);
END
$$;

CREATE FUNCTION public.ctm_returned_source_visible(resource text, data jsonb) RETURNS boolean
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
BEGIN
 IF resource='notification' THEN RETURN public.ctm_correction_notice_visible(data->>'key'); END IF;
 IF resource='auditevent' THEN
  IF data->>'source' IN ('tribunal.answerrevision','tribunal.fileversion') THEN
   RETURN public.ctm_filing_source_formal(split_part(data->>'source','.',2),(data->>'source_id')::uuid);
  END IF;
  RETURN true;
 END IF;
 IF NOT public.ctm_is_council() THEN RETURN true; END IF;
 IF resource='answerrevision' THEN RETURN public.ctm_filing_source_formal(resource,(data->>'id')::uuid); END IF;
 IF resource='attachment' THEN
  RETURN (data->>'application_id') IS NULL OR EXISTS(SELECT 1 FROM public.tribunal_fileversion v WHERE v.attachment_id=(data->>'id')::uuid AND public.ctm_filing_source_formal('fileversion',v.id));
 END IF;
 RETURN true;
END
$$;

CREATE OR REPLACE FUNCTION public.ctm_file_row_readable(attachment_id uuid,file_id uuid,version_number integer) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
 SELECT EXISTS(SELECT 1 FROM public.tribunal_attachment a WHERE a.id=attachment_id
   AND public.ctm_actor_role() IS NOT NULL AND (
      (public.ctm_is_council() AND public.ctm_attachment_visible(a.id) AND public.ctm_filing_source_formal('fileversion',file_id)) OR
      public.ctm_decree_released(file_id) OR
      (a.owner_id=public.ctm_actor_id() AND a.visibility<>'council' AND NOT EXISTS(
         SELECT 1 FROM public.tribunal_fileversion v WHERE v.attachment_id=a.id AND v.number>version_number))))
$$;
