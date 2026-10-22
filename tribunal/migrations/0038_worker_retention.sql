CREATE FUNCTION public.ctm_process_retention(clock_time timestamptz) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public AS $$
DECLARE a public.tribunal_application; deadline timestamptz; object_key text; notice_key text;
 warned integer=0; expired integer=0; held integer=0; changed integer;
BEGIN
 IF NOT public.ctm_worker_caller() AND NOT public.ctm_migration_caller() THEN
  RAISE EXCEPTION 'Worker retention only' USING ERRCODE='42501'; END IF;
 IF NOT public.ctm_migration_caller() AND abs(extract(epoch FROM (clock_time-statement_timestamp())))>60 THEN
  RAISE EXCEPTION 'Retention uses the current server clock' USING ERRCODE='42501'; END IF;
 FOR a IN SELECT * FROM public.tribunal_application WHERE status='draft' AND submitted_at IS NULL
   AND last_activity<=clock_time-interval '173 days' ORDER BY last_activity,id LIMIT 100 FOR UPDATE SKIP LOCKED LOOP
  IF EXISTS(SELECT 1 FROM public.tribunal_checkoutintent i WHERE i.application_id=a.id) THEN held=held+1; CONTINUE; END IF;
  deadline=a.last_activity+interval '180 days';
  IF deadline<=clock_time THEN
   FOR object_key IN SELECT f.object_key FROM public.tribunal_fileversion f
      JOIN public.tribunal_attachment attachment ON attachment.id=f.attachment_id WHERE attachment.application_id=a.id LOOP
    INSERT INTO public.tribunal_outbox(id,created_at,key,kind,payload,due_at,attempts,last_error)
     VALUES(gen_random_uuid(),statement_timestamp(),'cleanup:'||encode(sha256(convert_to(object_key,'UTF8')),'hex'),
      'private_orphan_cleanup',jsonb_build_object('object_key',object_key),clock_time,0,'') ON CONFLICT(key) DO NOTHING;
   END LOOP;
   DELETE FROM public.tribunal_documenttext WHERE file_id IN(SELECT f.id FROM public.tribunal_fileversion f JOIN public.tribunal_attachment t ON t.id=f.attachment_id WHERE t.application_id=a.id);
   DELETE FROM public.tribunal_filetechnicalevent WHERE file_id IN(SELECT f.id FROM public.tribunal_fileversion f JOIN public.tribunal_attachment t ON t.id=f.attachment_id WHERE t.application_id=a.id);
   DELETE FROM public.tribunal_fileversion WHERE attachment_id IN(SELECT t.id FROM public.tribunal_attachment t WHERE t.application_id=a.id);
   DELETE FROM public.tribunal_attachment WHERE application_id=a.id;
   DELETE FROM public.tribunal_answerrevision WHERE application_id=a.id;
   UPDATE public.tribunal_application SET status='expired',current_version=0 WHERE id=a.id;
   INSERT INTO public.tribunal_auditevent(id,created_at,actor_id,action,source,source_id,case_id,metadata)
    VALUES(gen_random_uuid(),clock_time,NULL,'draft_expired','tribunal.application',a.id,a.case_id,'{}');
   expired=expired+1;
  ELSE
   notice_key='draft-expiry:'||a.id::text||':'||to_char(deadline AT TIME ZONE 'UTC','YYYY-MM-DD"T"HH24:MI:SS.US')||'+00:00';
   INSERT INTO public.tribunal_notification(id,created_at,recipient_id,key,kind,payload)
    VALUES(gen_random_uuid(),clock_time,a.owner_id,notice_key,'draft_expiring',jsonb_build_object('expires_at',deadline,'application',a.id))
    ON CONFLICT(recipient_id,key) DO NOTHING;
   GET DIAGNOSTICS changed=ROW_COUNT;
   IF changed>0 THEN
    INSERT INTO public.tribunal_outbox(id,created_at,key,kind,recipient_id,payload,due_at,attempts,last_error)
     VALUES(gen_random_uuid(),clock_time,notice_key,'draft_expiring',a.owner_id,jsonb_build_object('expires_at',deadline,'application',a.id),clock_time,0,'')
     ON CONFLICT(key) DO NOTHING;
    warned=warned+1;
   END IF;
  END IF;
 END LOOP;
 RETURN jsonb_build_object('warned',warned,'expired',expired,'held',held);
END $$;
REVOKE ALL ON FUNCTION public.ctm_process_retention(timestamptz) FROM PUBLIC;

CREATE FUNCTION public.ctm_worker_finance_guard() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public AS $$
BEGIN
 IF TG_TABLE_NAME='tribunal_feeobligation' THEN
  IF public.ctm_worker_caller() THEN RAISE EXCEPTION 'Worker cannot change fee facts' USING ERRCODE='42501'; END IF;
  RETURN NEW;
 END IF;
 IF public.ctm_worker_caller() AND NOT (
   OLD.id=public.ctm_context_uuid('ctm.payment_recovery') AND public.ctm_paid_filing_actor(OLD.id) IS NOT NULL
   AND OLD.state IN ('paid','needs_review','finalized') AND NEW.state IN ('needs_review','finalized')
   AND NEW.failure IN ('','Paid filing requires reconciliation')
   AND (to_jsonb(NEW)-ARRAY['state','failure']) IS NOT DISTINCT FROM (to_jsonb(OLD)-ARRAY['state','failure'])) THEN
  RAISE EXCEPTION 'Worker can only recover a verified paid candidate' USING ERRCODE='42501'; END IF;
 RETURN NEW;
END $$;
REVOKE ALL ON FUNCTION public.ctm_worker_finance_guard() FROM PUBLIC;
CREATE TRIGGER worker_finance_guard BEFORE UPDATE ON public.tribunal_checkoutintent FOR EACH ROW EXECUTE FUNCTION public.ctm_worker_finance_guard();

CREATE TRIGGER worker_fee_guard BEFORE UPDATE ON public.tribunal_feeobligation FOR EACH ROW EXECUTE FUNCTION public.ctm_worker_finance_guard();
