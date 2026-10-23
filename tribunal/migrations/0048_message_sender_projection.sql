CREATE FUNCTION public.ctm_message_sender_names(targets uuid[])
RETURNS TABLE(message_id uuid, sender_name text)
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
BEGIN
 IF public.ctm_worker_caller() OR public.ctm_actor_role() IS NULL
    OR coalesce(cardinality(targets),0)>250 THEN RETURN; END IF;
 RETURN QUERY SELECT m.id,btrim(a.first_name||' '||a.last_name)
 FROM public.tribunal_message m JOIN public.tribunal_account a ON a.id=m.sender_id
 WHERE m.id=ANY(targets) AND public.ctm_message_visible(m.id);
END $$;
REVOKE ALL ON FUNCTION public.ctm_message_sender_names(uuid[]) FROM PUBLIC;
