CREATE FUNCTION public.ctm_call_readable() RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
 SELECT public.ctm_is_council()
$$;

CREATE FUNCTION public.ctm_call_writable(data jsonb) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
 SELECT coalesce(data->>'actor_id'=public.ctm_actor_id()::text
  AND length(btrim(data->>'outcome')) BETWEEN 1 AND 150 AND length(data->>'notes')<=100000
  AND EXISTS(SELECT 1 FROM public.tribunal_case c JOIN public.tribunal_party p ON p.case_id=c.id
    WHERE c.id=(data->>'case_id')::uuid AND p.id=(data->>'party_id')::uuid
     AND (public.ctm_actor_role() IN ('admin','secretary') OR
       (public.ctm_is_council() AND c.assigned_member_id=public.ctm_actor_id()))),false)
$$;

CREATE FUNCTION public.ctm_guard_checkout_link() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public AS $$
BEGIN
 IF TG_OP='UPDATE' THEN
  IF OLD.checkout_url<>'' AND (NEW.checkout_url,NEW.checkout_expires_at) IS DISTINCT FROM (OLD.checkout_url,OLD.checkout_expires_at) THEN
   RAISE EXCEPTION 'Original provider checkout link is retained' USING ERRCODE='42501';
  END IF;
  IF (NEW.checkout_url,NEW.checkout_expires_at) IS NOT DISTINCT FROM (OLD.checkout_url,OLD.checkout_expires_at) THEN RETURN NEW; END IF;
 ELSIF NEW.checkout_url='' AND NEW.checkout_expires_at IS NULL THEN RETURN NEW;
 END IF;
 IF NEW.checkout_url<>'' AND NEW.checkout_url !~ '^https://checkout[.]stripe[.]com(:443)?/' THEN
  RAISE EXCEPTION 'Checkout link is outside the provider host' USING ERRCODE='42501';
 END IF;
 IF NEW.id::text IS DISTINCT FROM current_setting('ctm.checkout_created',true)
   OR NEW.provider_reference IS DISTINCT FROM current_setting('ctm.created_reference',true)
   OR NOT EXISTS(SELECT 1 FROM public.tribunal_application a WHERE a.id=NEW.application_id AND a.owner_id=public.ctm_actor_id()) THEN
  RAISE EXCEPTION 'Checkout link requires the bound provider-create context' USING ERRCODE='42501';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER checkout_link_provenance BEFORE INSERT OR UPDATE ON public.tribunal_checkoutintent FOR EACH ROW EXECUTE FUNCTION public.ctm_guard_checkout_link();

CREATE FUNCTION public.ctm_guard_recording_scope() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public AS $$
DECLARE target_case uuid; target_proceeding uuid; source_kind text; attachment public.tribunal_attachment;
BEGIN
 IF TG_OP='UPDATE' THEN
  IF (NEW.file_id,NEW.report_id,NEW.appointment_id) IS DISTINCT FROM (OLD.file_id,OLD.report_id,OLD.appointment_id)
    OR (OLD.finalized_at IS NOT NULL AND (NEW.finalized_at,NEW.notice_recorded) IS DISTINCT FROM (OLD.finalized_at,OLD.notice_recorded)) THEN
   RAISE EXCEPTION 'Recording source and finalization are retained' USING ERRCODE='42501';
  END IF;
 END IF;
 IF (NEW.report_id IS NULL)=(NEW.appointment_id IS NULL) THEN
  RAISE EXCEPTION 'Exactly one recording source is required' USING ERRCODE='42501';
 END IF;
 SELECT a.* INTO attachment FROM public.tribunal_attachment a JOIN public.tribunal_fileversion f ON f.attachment_id=a.id WHERE f.id=NEW.file_id;
 IF NEW.report_id IS NOT NULL THEN
  SELECT r.case_id,r.proceeding_id,r.kind INTO target_case,target_proceeding,source_kind
    FROM public.tribunal_report report JOIN public.tribunal_reportrequest r ON r.id=report.request_id WHERE report.id=NEW.report_id;
 ELSE
  SELECT agenda.case_id INTO target_case FROM public.tribunal_testimonyappointment appointment
    JOIN public.tribunal_agendaitem agenda ON agenda.id=appointment.agenda_id WHERE appointment.id=NEW.appointment_id;
 END IF;
 IF attachment.case_id IS DISTINCT FROM target_case OR attachment.visibility<>'council'
   OR attachment.application_id IS NOT NULL OR attachment.report_request_id IS NOT NULL
   OR (NEW.report_id IS NOT NULL AND attachment.proceeding_id IS DISTINCT FROM target_proceeding)
   OR source_kind IN ('medical','psychological') THEN
  RAISE EXCEPTION 'Recording source is outside its case, proceeding or privacy scope' USING ERRCODE='42501';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER recording_source_scope BEFORE INSERT OR UPDATE ON public.tribunal_recording FOR EACH ROW EXECUTE FUNCTION public.ctm_guard_recording_scope();
