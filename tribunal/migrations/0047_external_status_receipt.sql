CREATE FUNCTION public.ctm_external_status_receipt() RETURNS jsonb
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
 SELECT jsonb_build_object(
 'state', CASE WHEN r.expires_at<=statement_timestamp() THEN 'expired'
   WHEN r.state='completed' AND report.id IS NOT NULL THEN 'completed'
   WHEN r.state='cancelled' THEN 'cancelled'
   WHEN r.state='closed' OR c.status<>'open' OR p.status<>'open' THEN 'closed'
   WHEN r.state='sent' THEN 'active' ELSE 'unavailable' END,
 'expires_at',r.expires_at,
 'receipt',CASE WHEN r.state='completed' AND report.id IS NOT NULL AND r.expires_at>statement_timestamp()
   THEN jsonb_build_object('report_id',report.id,'completed_at',report.created_at) ELSE NULL END)
 FROM public.tribunal_reportrequest r
 JOIN public.tribunal_proceeding p ON p.id=r.proceeding_id AND p.case_id=r.case_id
 JOIN public.tribunal_case c ON c.id=r.case_id
 LEFT JOIN public.tribunal_report report ON report.request_id=r.id AND report.method='external' AND report.author_id IS NULL
 WHERE r.id=public.ctm_context_uuid('ctm.external_request') AND r.kind='external_priest'
 AND length(r.token_hash)=64 AND r.token_hash=current_setting('ctm.external_digest',true)
 AND r.expires_at IS NOT NULL
$$;
REVOKE ALL ON FUNCTION public.ctm_external_status_receipt() FROM PUBLIC;
