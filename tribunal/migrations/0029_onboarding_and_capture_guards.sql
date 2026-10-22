CREATE FUNCTION public.ctm_pending_readable(data jsonb) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
 SELECT coalesce(public.ctm_actor_role() IN ('admin','secretary') OR EXISTS(
  SELECT 1 FROM public.tribunal_account a WHERE a.id=public.ctm_actor_id() AND a.is_active AND a.email_verified
   AND a.role='applicant' AND lower(a.email)=data->>'email'),false)
$$;

CREATE FUNCTION public.ctm_pending_writable(data jsonb, operation text) RETURNS boolean
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
BEGIN
 IF public.ctm_actor_role() IN ('admin','secretary') THEN
  RETURN (operation<>'insert' OR (data->>'actor_id'=public.ctm_actor_id()::text AND data->>'state'='pending'
   AND data->>'activated_party_id' IS NULL)) AND data->>'email'=lower(btrim(data->>'email'));
 END IF;
 IF operation='insert' OR public.ctm_pending_readable(data) IS NOT TRUE THEN RETURN false; END IF;
 IF data->>'state'='needs_review' THEN
  RETURN NOT EXISTS(SELECT 1 FROM public.tribunal_account issuer WHERE issuer.id=(data->>'actor_id')::uuid
    AND issuer.is_active AND issuer.role IN ('admin','secretary'));
 END IF;
 RETURN data->>'state'='activated' AND EXISTS(SELECT 1 FROM public.tribunal_party party
   JOIN public.tribunal_account a ON a.id=party.account_id
   JOIN public.tribunal_account issuer ON issuer.id=(data->>'actor_id')::uuid
   WHERE party.id=(data->>'activated_party_id')::uuid AND party.case_id=(data->>'case_id')::uuid
     AND a.id=public.ctm_actor_id() AND party.person_id=a.person_id AND issuer.is_active AND issuer.role IN ('admin','secretary'));
END $$;

CREATE FUNCTION public.ctm_media_status(target uuid) RETURNS jsonb
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
 SELECT CASE WHEN EXISTS(SELECT 1 FROM public.tribunal_recording x WHERE x.file_id=target AND public.ctm_media_recording_visible(x.id))
 THEN (SELECT jsonb_build_object('run_id',run.id,'state',CASE WHEN run.state='completed' THEN 'succeeded' ELSE run.state END,
   'attempt',run.attempt,'engine',run.engine,'updated_at',NULL,'safe_error',CASE WHEN run.state='failed'
    THEN 'Processing failed; the original is retained.' ELSE '' END)
  FROM public.tribunal_processingrun run WHERE run.file_id=target AND run.purpose='transcription' ORDER BY run.attempt DESC LIMIT 1) END
$$;

CREATE FUNCTION public.ctm_supplement_manifest_valid(data jsonb) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
 SELECT length(data->>'text')<=100000 AND jsonb_typeof(data->'manifest')='array'
 AND NOT EXISTS(SELECT 1 FROM jsonb_array_elements(data->'manifest') item WHERE NOT EXISTS(
  SELECT 1 FROM public.tribunal_fileversion f JOIN public.tribunal_attachment a ON a.id=f.attachment_id
   JOIN public.tribunal_application app ON app.id=a.application_id
  WHERE f.id::text=item->>'id' AND a.application_id=(data->>'application_id')::uuid
   AND a.owner_id=public.ctm_actor_id() AND a.visibility='own' AND a.report_request_id IS NULL
   AND a.case_id=app.case_id AND f.sha256=item->>'sha256'
   AND NOT EXISTS(SELECT 1 FROM public.tribunal_fileversion newer WHERE newer.attachment_id=a.id AND newer.number>f.number)))
$$;

CREATE FUNCTION public.ctm_guard_twenty() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public AS $$
BEGIN
 IF TG_TABLE_NAME='tribunal_recording' THEN
  IF (NEW.captured_by_id,NEW.duration_ms,NEW.recording_notice) IS DISTINCT FROM (OLD.captured_by_id,OLD.duration_ms,OLD.recording_notice) THEN
   RAISE EXCEPTION 'Original capture author, duration and notice are retained' USING ERRCODE='42501';
  END IF;
  RETURN NEW;
 END IF;
 IF TG_TABLE_NAME='tribunal_historicalworkspace' THEN
  IF NEW.actor_id IS DISTINCT FROM OLD.actor_id OR (OLD.finalized_case_id IS NOT NULL
     AND (NEW.payload,NEW.finalized_case_id) IS DISTINCT FROM (OLD.payload,OLD.finalized_case_id)) THEN
   RAISE EXCEPTION 'Historical workspace author and published source are retained' USING ERRCODE='42501';
  END IF;
  RETURN NEW;
 END IF;
 IF (NEW.case_id,NEW.actor_id,NEW.email,NEW.first_name,NEW.last_name) IS DISTINCT FROM (OLD.case_id,OLD.actor_id,OLD.email,OLD.first_name,OLD.last_name)
  OR (OLD.state IN ('activated','cancelled') AND (NEW.state,NEW.activated_party_id) IS DISTINCT FROM (OLD.state,OLD.activated_party_id)) THEN
  RAISE EXCEPTION 'Authorized pending association provenance is retained' USING ERRCODE='42501';
 END IF;
 IF NEW.state='activated' AND NOT EXISTS(SELECT 1 FROM public.tribunal_party p JOIN public.tribunal_account a ON a.id=p.account_id
    JOIN public.tribunal_account issuer ON issuer.id=NEW.actor_id AND issuer.is_active AND issuer.role IN ('admin','secretary')
    WHERE p.id=NEW.activated_party_id AND p.case_id=NEW.case_id AND lower(a.email)=NEW.email AND a.email_verified AND a.is_active AND a.role='applicant'
      AND p.person_id=a.person_id) THEN
  RAISE EXCEPTION 'Activation must match the verified applicant and exact case' USING ERRCODE='42501';
 END IF;
 RETURN NEW;
END $$;
