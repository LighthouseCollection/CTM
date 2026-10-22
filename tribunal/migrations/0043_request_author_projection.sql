CREATE FUNCTION public.ctm_request_author_names(targets uuid[])
RETURNS TABLE(request_id uuid, author_name text)
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
BEGIN
 IF public.ctm_worker_caller() OR public.ctm_actor_role() IS NULL
    OR coalesce(cardinality(targets),0)>250 THEN RETURN; END IF;
 RETURN QUERY SELECT r.id, btrim(a.first_name||' '||a.last_name)
 FROM public.tribunal_reportrequest r JOIN public.tribunal_account a ON a.id=r.author_id
 LEFT JOIN public.tribunal_party subject ON subject.id=r.subject_id AND subject.case_id=r.case_id
 WHERE r.id=ANY(targets) AND (public.ctm_is_council() OR (
   public.ctm_actor_role()='applicant' AND r.sent_at IS NOT NULL AND r.state<>'draft'
   AND r.kind NOT IN ('interview','external_priest') AND subject.account_id=public.ctm_actor_id()));
END $$;
REVOKE ALL ON FUNCTION public.ctm_request_author_names(uuid[]) FROM PUBLIC;
