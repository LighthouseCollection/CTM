CREATE FUNCTION public.ctm_payment_scope(target uuid) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
 SELECT EXISTS(SELECT 1 FROM public.tribunal_checkoutintent i WHERE i.id=target AND (
   (i.id::text=current_setting('ctm.payment_candidate',true)
    AND left(current_setting('ctm.payment_session',true),3)='cs_'
    AND (coalesce(i.provider_reference,'')='' OR i.provider_reference=current_setting('ctm.payment_session',true)))
   OR (i.payment_reference<>'' AND i.payment_reference=current_setting('ctm.payment_reference',true))
   OR (i.id::text=current_setting('ctm.payment_recovery',true) AND public.ctm_paid_filing_actor(i.id) IS NOT NULL)))
$$;

CREATE FUNCTION public.ctm_finance_readable(resource text,data jsonb) RETURNS boolean
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
DECLARE role_name text=public.ctm_actor_role(); target uuid=(data->>'application_id')::uuid;
BEGIN
 IF resource='checkoutintent' AND public.ctm_payment_scope((data->>'id')::uuid) THEN RETURN true; END IF;
 IF resource IN ('feeobligation','paymentevent') AND EXISTS(
    SELECT 1 FROM public.tribunal_checkoutintent i WHERE i.application_id=target AND public.ctm_payment_scope(i.id)) THEN RETURN true; END IF;
 IF role_name IS NULL THEN RETURN false; END IF;
 IF EXISTS(SELECT 1 FROM public.tribunal_application a WHERE a.id=target AND a.owner_id=public.ctm_actor_id()) THEN RETURN true; END IF;
 IF role_name IN ('admin','secretary') THEN
   RETURN resource='feeobligation' OR EXISTS(SELECT 1 FROM public.tribunal_application a WHERE a.id=target AND a.submitted_at IS NOT NULL)
      OR (resource='checkoutintent' AND data->>'state' IN ('paid','needs_review','finalized'))
      OR (resource='paymentevent' AND data->>'kind' IN ('paid','chargeback','refunded','dispute_won','dispute_lost','dispute_warning_closed'));
 END IF;
 RETURN resource IN ('feeobligation','completenessreview') AND public.ctm_application_visible(target);
END $$;

CREATE FUNCTION public.ctm_review_readable(data jsonb) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
 SELECT EXISTS(SELECT 1 FROM public.tribunal_submission s
   WHERE s.id=(data->>'submission_id')::uuid AND public.ctm_application_visible(s.application_id))
$$;

CREATE FUNCTION public.ctm_fee_can_waive(target uuid) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
 SELECT public.ctm_actor_role() IN ('admin','secretary') AND EXISTS(
   SELECT 1 FROM public.tribunal_application a WHERE a.id=target AND a.submitted_at IS NULL
    AND a.status='draft' AND NOT EXISTS(SELECT 1 FROM public.tribunal_checkoutintent i
      WHERE i.application_id=a.id AND i.state IN ('pending','processing','paid','needs_review')))
$$;

CREATE FUNCTION public.ctm_finance_writable(resource text,data jsonb) RETURNS boolean
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
DECLARE actor uuid=public.ctm_actor_id(); role_name text=public.ctm_actor_role(); target uuid=(data->>'application_id')::uuid;
BEGIN
 CASE resource
 WHEN 'feeobligation' THEN
   IF (data->>'amount_minor')::bigint<>25000 OR data->>'currency'<>'USD' THEN RETURN false; END IF;
   IF data->>'status'='waived' THEN RETURN data->>'waived_by_id'=actor::text AND public.ctm_fee_can_waive(target); END IF;
   IF data->>'status'='paid' THEN RETURN EXISTS(SELECT 1 FROM public.tribunal_paymentevent e
     WHERE e.application_id=target AND e.kind='paid' AND e.amount_minor=25000 AND e.currency='USD')
       AND (public.ctm_finance_readable(resource,data)); END IF;
   RETURN data->>'status'='due' AND data->>'waived_by_id' IS NULL AND EXISTS(
      SELECT 1 FROM public.tribunal_application a WHERE a.id=target AND a.owner_id=actor AND a.status='draft' AND a.submitted_at IS NULL);
 WHEN 'paymentevent' THEN
   RETURN data->>'provider_event_id'=current_setting('ctm.payment_event',true)
     AND data->>'kind' IN ('paid','processing','expired','failed','chargeback','refunded','dispute_won','dispute_lost','dispute_warning_closed')
     AND (data->>'amount_minor')::bigint>0 AND (data->>'amount_minor')::bigint<=25000 AND data->>'currency'='USD'
     AND EXISTS(SELECT 1 FROM public.tribunal_checkoutintent i WHERE i.application_id=target
       AND public.ctm_payment_scope(i.id)
       AND coalesce(i.provider_reference,current_setting('ctm.payment_session',true))=data->>'provider_reference');
 WHEN 'checkoutintent' THEN
   IF public.ctm_payment_scope((data->>'id')::uuid) THEN
     RETURN data->>'state' IN ('pending','processing','paid','needs_review','finalized','expired','failed');
   END IF;
   IF data->>'id'=current_setting('ctm.checkout_created',true) THEN
     RETURN data->>'provider_reference'=current_setting('ctm.created_reference',true)
       AND EXISTS(SELECT 1 FROM public.tribunal_application a WHERE a.id=target AND a.owner_id=actor);
   END IF;
   RETURN data->>'state'='pending' AND coalesce(data->>'provider_reference','')=''
     AND coalesce(data->>'payment_reference','')=''
     AND EXISTS(SELECT 1 FROM public.tribunal_application a
       JOIN public.tribunal_answerrevision r ON r.application_id=a.id AND r.number=a.current_version
       JOIN public.tribunal_feeobligation f ON f.application_id=a.id
       WHERE a.id=target AND a.owner_id=actor AND a.status='draft' AND NOT a.duplicate_hold
         AND f.status='due' AND r.id=(data->>'revision_id')::uuid);
 WHEN 'completenessreview' THEN
   RETURN role_name IN ('admin','secretary') AND data->>'actor_id'=actor::text
     AND data->>'result' IN ('accept','reject') AND (data->>'result'<>'reject' OR btrim(data->>'instructions')<>'')
     AND EXISTS(SELECT 1 FROM public.tribunal_submission s
       JOIN public.tribunal_application a ON a.id=s.application_id
       JOIN public.tribunal_proceeding p ON p.id=a.proceeding_id
       JOIN public.tribunal_case c ON c.id=a.case_id
       WHERE s.id=(data->>'submission_id')::uuid AND a.kind='petition' AND a.status='submitted'
         AND p.status='open' AND c.status='open'
         AND NOT EXISTS(SELECT 1 FROM public.tribunal_submission newer
           WHERE newer.application_id=a.id AND (newer.created_at,newer.id)>(s.created_at,s.id)));
 ELSE RETURN false;
 END CASE;
END $$;

CREATE FUNCTION public.ctm_finance_notice(resource text,data jsonb) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
 SELECT EXISTS(SELECT 1 FROM public.tribunal_paymentevent e
   JOIN public.tribunal_checkoutintent i ON i.application_id=e.application_id AND i.provider_reference=e.provider_reference
   WHERE e.provider_event_id=current_setting('ctm.payment_event',true) AND public.ctm_payment_scope(i.id)
   AND CASE resource
     WHEN 'auditevent' THEN data->>'actor_id' IS NULL AND data->>'action'='finance_event_verified'
       AND data->>'source'='tribunal.paymentevent' AND data->>'source_id'=e.id::text
     WHEN 'notification' THEN data->>'kind'='payment_finance_review' AND EXISTS(
       SELECT 1 FROM public.tribunal_account recipient WHERE recipient.id=(data->>'recipient_id')::uuid
         AND recipient.is_active AND recipient.role IN ('admin','secretary')
         AND data->>'key'='payment_finance_review:'||e.id::text||':'||recipient.id::text)
     ELSE false END)
$$;

CREATE FUNCTION public.ctm_preserve_finance_context() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog,public AS $$
BEGIN
 IF NEW.application_id IS DISTINCT FROM OLD.application_id THEN
   RAISE EXCEPTION 'Original financial obligation cannot be reassigned' USING ERRCODE='23514';
 END IF;
 IF TG_TABLE_NAME='tribunal_checkoutintent' THEN
   IF NEW.revision_id IS DISTINCT FROM OLD.revision_id OR NEW.attestation IS DISTINCT FROM OLD.attestation
     OR NEW.manifest IS DISTINCT FROM OLD.manifest
     OR (coalesce(OLD.provider_reference,'')<>'' AND NEW.provider_reference IS DISTINCT FROM OLD.provider_reference)
     OR (OLD.payment_reference<>'' AND NEW.payment_reference IS DISTINCT FROM OLD.payment_reference) THEN
     RAISE EXCEPTION 'Frozen checkout identity and source cannot be rewritten' USING ERRCODE='23514';
   END IF;
   IF OLD.state IN ('paid','needs_review','finalized') AND NEW.state NOT IN ('paid','needs_review','finalized') THEN
     RAISE EXCEPTION 'Successful payment cannot become unpaid' USING ERRCODE='23514';
   END IF;
   IF OLD.state='finalized' AND NEW.state<>'finalized' THEN
     RAISE EXCEPTION 'Finalized checkout cannot be reopened' USING ERRCODE='23514';
   END IF;
 ELSIF TG_TABLE_NAME='tribunal_feeobligation' THEN
   IF NEW.amount_minor<>OLD.amount_minor OR NEW.currency<>OLD.currency
     OR (OLD.status IN ('paid','waived','historical_exempt') AND NEW.status='due') THEN
     RAISE EXCEPTION 'Satisfied filing obligation cannot be reset or repriced' USING ERRCODE='23514';
   END IF;
   IF NEW.waived_by_id IS DISTINCT FROM OLD.waived_by_id
     AND NOT (OLD.status='due' AND NEW.status='waived' AND NEW.waived_by_id IS NOT NULL) THEN
     RAISE EXCEPTION 'Original waiver attribution cannot be rewritten' USING ERRCODE='23514';
   END IF;
 END IF;
 RETURN NEW;
END $$;

CREATE TRIGGER preserve_finance_context BEFORE UPDATE ON public.tribunal_checkoutintent
 FOR EACH ROW EXECUTE FUNCTION public.ctm_preserve_finance_context();
CREATE TRIGGER preserve_finance_context BEFORE UPDATE ON public.tribunal_feeobligation
 FOR EACH ROW EXECUTE FUNCTION public.ctm_preserve_finance_context();
