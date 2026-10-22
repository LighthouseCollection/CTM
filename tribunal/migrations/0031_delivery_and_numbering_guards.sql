CREATE FUNCTION public.ctm_allocate_case_number(target date) RETURNS text
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public AS $$
DECLARE counter integer; owner_name text; caller_name text;
BEGIN
 SELECT pg_get_userbyid(c.relowner) INTO owner_name FROM pg_class c WHERE c.oid='public.tribunal_casenumbercounter'::regclass;
 caller_name=coalesce(nullif(current_setting('role',true),'none'),session_user);
 IF caller_name IS DISTINCT FROM owner_name AND (target IS DISTINCT FROM (statement_timestamp() AT TIME ZONE 'America/Los_Angeles')::date OR NOT EXISTS(
  SELECT 1 FROM public.tribunal_application app JOIN public.tribunal_account a ON a.id=app.owner_id
   JOIN public.tribunal_feeobligation fee ON fee.application_id=app.id
  WHERE app.id::text=current_setting('ctm.numbering_application',true) AND app.owner_id=public.ctm_actor_id()
   AND a.is_active AND a.email_verified AND app.kind='petition' AND app.status='draft' AND app.submitted_at IS NULL
   AND app.case_id IS NULL AND NOT app.duplicate_hold AND fee.status IN ('paid','waived','historical_exempt'))) THEN
  RAISE EXCEPTION 'Number allocation requires the current eligible filing context' USING ERRCODE='42501';
 END IF;
 INSERT INTO public.tribunal_casenumbercounter(date,last_value) VALUES(target,0) ON CONFLICT DO NOTHING;
 SELECT last_value INTO counter FROM public.tribunal_casenumbercounter WHERE date=target FOR UPDATE;
 IF counter>=99 THEN RAISE EXCEPTION 'Daily numbering capacity reached' USING ERRCODE='23514'; END IF;
 UPDATE public.tribunal_casenumbercounter SET last_value=counter+1 WHERE date=target;
 RETURN to_char(target,'YYYYMMDD')||'-'||lpad((counter+1)::text,2,'0');
END $$;

CREATE FUNCTION public.ctm_message_delivery_valid(target uuid,recipient uuid) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
 SELECT EXISTS(SELECT 1 FROM public.tribunal_messagerecipient r JOIN public.tribunal_message m ON m.id=r.message_id
  JOIN public.tribunal_party p ON p.id=r.party_id JOIN public.tribunal_account a ON a.id=p.account_id
  WHERE m.id=target AND p.case_id=m.case_id AND a.id=recipient AND a.is_active AND a.email_verified AND a.role='applicant')
$$;

CREATE FUNCTION public.ctm_draft_warning_current(target uuid,deadline timestamptz,recipient uuid) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
 SELECT EXISTS(SELECT 1 FROM public.tribunal_application a WHERE a.id=target AND a.owner_id=recipient
  AND a.status='draft' AND a.submitted_at IS NULL AND a.last_activity+interval '180 days'=deadline
  AND deadline>statement_timestamp() AND deadline<=statement_timestamp()+interval '7 days'
  AND NOT EXISTS(SELECT 1 FROM public.tribunal_checkoutintent c WHERE c.application_id=a.id))
$$;

CREATE FUNCTION public.ctm_guard_delivery_sources() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog,public AS $$
BEGIN
 IF TG_TABLE_NAME='tribunal_casenumbercounter' THEN
  IF NEW.date IS DISTINCT FROM OLD.date OR NEW.last_value<>OLD.last_value+1 OR NEW.last_value>99 THEN
   RAISE EXCEPTION 'Daily counter advances once without date rebinding' USING ERRCODE='42501';
  END IF;
  RETURN NEW;
 END IF;
 IF TG_TABLE_NAME='tribunal_messagerecipient' THEN
  IF (NEW.message_id,NEW.party_id) IS DISTINCT FROM (OLD.message_id,OLD.party_id)
    OR (OLD.read_at IS NOT NULL AND NEW.read_at IS DISTINCT FROM OLD.read_at) THEN
   RAISE EXCEPTION 'Recipient copy and first acknowledgement are retained' USING ERRCODE='42501';
  END IF;
  RETURN NEW;
 END IF;
 IF (OLD.delivered_at IS NOT NULL AND NEW.delivered_at IS DISTINCT FROM OLD.delivered_at)
   OR (OLD.discarded_at IS NOT NULL AND NEW.discarded_at IS DISTINCT FROM OLD.discarded_at)
   OR (NEW.delivered_at IS NOT NULL AND NEW.discarded_at IS NOT NULL) THEN
  RAISE EXCEPTION 'Delivery and discard evidence cannot be erased or conflated' USING ERRCODE='42501';
 END IF;
 RETURN NEW;
END $$;
