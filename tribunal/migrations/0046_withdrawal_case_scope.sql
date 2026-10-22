CREATE FUNCTION public.ctm_withdrawal_can_close(target uuid) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
 SELECT coalesce(current_setting('ctm.core_operation',true)='withdraw'
 AND target=public.ctm_context_uuid('ctm.core_target')
 AND public.ctm_actor_role() IS NOT NULL
 AND EXISTS(SELECT 1 FROM public.tribunal_application a
 JOIN public.tribunal_account owner ON owner.id=a.owner_id
 JOIN public.tribunal_party p ON p.id=a.party_id AND p.case_id=a.case_id AND p.person_id=owner.person_id
 JOIN public.tribunal_case c ON c.id=a.case_id AND c.status='open'
 WHERE a.id=target AND a.kind='petition' AND a.status='withdrawn' AND a.submitted_at IS NOT NULL
 AND (a.owner_id=public.ctm_actor_id() OR public.ctm_actor_role()='admin')
 AND p.account_id=a.owner_id AND p.withdrawn_at IS NOT NULL
 AND NOT EXISTS(SELECT 1 FROM public.tribunal_party remaining
 WHERE remaining.case_id=a.case_id AND remaining.participating AND remaining.withdrawn_at IS NULL)),false)
$$;
REVOKE ALL ON FUNCTION public.ctm_withdrawal_can_close(uuid) FROM PUBLIC;

CREATE FUNCTION public.ctm_closed_case_cleanup(target uuid) RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public AS $$
BEGIN
 IF public.ctm_actor_role() IS NULL
 OR current_setting('ctm.core_operation',true) IS DISTINCT FROM 'close'
 OR target IS DISTINCT FROM public.ctm_context_uuid('ctm.core_target')
 OR NOT coalesce(public.ctm_close_allowed(target),false)
 OR NOT EXISTS(SELECT 1 FROM public.tribunal_case c WHERE c.id=target AND c.status='closed')
 OR EXISTS(SELECT 1 FROM public.tribunal_proceeding p WHERE p.case_id=target AND p.status='open') THEN
  RAISE EXCEPTION 'Authorized completed case closure required' USING ERRCODE='42501';
 END IF;
 DELETE FROM public.tribunal_opencaseclaim WHERE case_id=target;
 UPDATE public.tribunal_reportrequest SET state='cancelled' WHERE case_id=target AND state='draft';
 UPDATE public.tribunal_reportrequest SET state='closed' WHERE case_id=target AND state='sent';
END $$;
REVOKE ALL ON FUNCTION public.ctm_closed_case_cleanup(uuid) FROM PUBLIC;
