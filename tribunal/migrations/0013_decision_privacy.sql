CREATE FUNCTION public.ctm_decision_readable(resource text,data jsonb) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
 SELECT public.ctm_is_council() OR CASE resource
  WHEN 'decree' THEN public.ctm_decree_released((data->>'signed_file_id')::uuid)
  WHEN 'decreerelease' THEN EXISTS(SELECT 1 FROM public.tribunal_party p
    WHERE p.id=(data->>'party_id')::uuid AND p.account_id=public.ctm_actor_id()
      AND public.ctm_actor_role()='applicant')
  ELSE false END
$$;

CREATE FUNCTION public.ctm_safe_council_pdf(target uuid,target_case uuid) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
 SELECT EXISTS(SELECT 1 FROM public.tribunal_fileversion v
  JOIN public.tribunal_attachment a ON a.id=v.attachment_id
  WHERE v.id=target AND a.case_id=target_case AND a.visibility='council'
    AND v.mime_type='application/pdf' AND (SELECT e.result FROM public.tribunal_filetechnicalevent e
      WHERE e.file_id=v.id AND e.task='scan' ORDER BY e.created_at DESC,e.id DESC LIMIT 1)='clean')
$$;

CREATE FUNCTION public.ctm_decision_writable(resource text,data jsonb) RETURNS boolean
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
DECLARE actor uuid=public.ctm_actor_id(); role_name text=public.ctm_actor_role();
BEGIN
 IF NOT public.ctm_is_council() OR data->>'actor_id' IS DISTINCT FROM actor::text THEN RETURN false; END IF;
 CASE resource
 WHEN 'decisionrevision' THEN
   RETURN public.ctm_council_proceeding_writer((data->>'proceeding_id')::uuid)
     AND data->>'type' IN ('diss-applicant','diss-respondent','diss-both','diss-conditional','null-granted','null-conditional','denied','deferred')
     AND btrim(data->>'grounds')<>'' AND jsonb_typeof(data->'entitlements')='object'
     AND (data->>'type' NOT IN ('diss-conditional','null-conditional') OR btrim(data->>'conditions')<>'')
     AND NOT EXISTS(SELECT 1 FROM jsonb_each_text(data->'entitlements') entry
       WHERE entry.value NOT IN ('certificate','notice_only') OR NOT EXISTS(
         SELECT 1 FROM public.tribunal_party party JOIN public.tribunal_proceeding p ON p.case_id=party.case_id
         WHERE p.id=(data->>'proceeding_id')::uuid AND party.id::text=entry.key));
 WHEN 'vote' THEN
   RETURN EXISTS(SELECT 1 FROM public.tribunal_decisionrevision d
     JOIN public.tribunal_account m ON m.id=(data->>'member_id')::uuid
     WHERE d.id=(data->>'decision_id')::uuid
       AND EXISTS(SELECT 1 FROM public.tribunal_proceeding p JOIN public.tribunal_case c ON c.id=p.case_id
           WHERE p.id=d.proceeding_id AND p.status='open' AND c.status='open')
       AND NOT EXISTS(SELECT 1 FROM public.tribunal_decisionrevision later WHERE later.proceeding_id=d.proceeding_id AND later.number>d.number)
       AND m.is_active AND m.role<>'applicant' AND (m.id=actor OR role_name IN ('admin','secretary'))
       AND data->>'choice' IN ('approve','deny','abstain'));
 WHEN 'presidentialapproval' THEN
   RETURN EXISTS(SELECT 1 FROM public.tribunal_decisionrevision d
     JOIN public.tribunal_proceeding p ON p.id=d.proceeding_id
     JOIN public.tribunal_case c ON c.id=p.case_id
     JOIN public.tribunal_account president ON president.id=(data->>'president_id')::uuid
     WHERE d.id=(data->>'decision_id')::uuid AND p.status='open' AND c.status='open'
       AND NOT EXISTS(SELECT 1 FROM public.tribunal_decisionrevision later WHERE later.proceeding_id=d.proceeding_id AND later.number>d.number)
       AND president.is_active AND president.role='president'
       AND (president.id=actor OR role_name IN ('admin','secretary')));
 WHEN 'signatureattestation' THEN
   RETURN EXISTS(SELECT 1 FROM public.tribunal_account signer
     JOIN public.tribunal_fileversion v ON v.id=(data->>'file_id')::uuid
     JOIN public.tribunal_attachment a ON a.id=v.attachment_id
     WHERE signer.id=(data->>'signer_id')::uuid AND signer.is_active AND signer.role='president'
       AND (signer.id=actor OR role_name IN ('admin','secretary'))
       AND public.ctm_safe_council_pdf(v.id,a.case_id)
       AND data->>'method' IN ('digital','signed_scan') AND data->'evidence'->>'confirmed_signed'='true');
 WHEN 'decree' THEN
   -- Decree has no actor column; handled by the dedicated branch below.
   RETURN false;
 WHEN 'decreerelease' THEN
   RETURN role_name IN ('admin','secretary') AND data->>'action' IN ('release','withdraw')
     AND EXISTS(SELECT 1 FROM public.tribunal_decree decree
       JOIN public.tribunal_decisionrevision d ON d.id=decree.decision_id
       JOIN public.tribunal_proceeding p ON p.id=d.proceeding_id
       JOIN public.tribunal_party party ON party.id=(data->>'party_id')::uuid AND party.case_id=p.case_id
       WHERE decree.id=(data->>'decree_id')::uuid AND d.entitlements->>party.id::text='certificate');
 ELSE RETURN false;
 END CASE;
END $$;

CREATE FUNCTION public.ctm_decree_writable(data jsonb) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
 SELECT public.ctm_actor_role() IN ('admin','secretary')
  AND data->>'language' IN ('en','ar','both') AND data->>'issued_at' IS NOT NULL
  AND EXISTS(SELECT 1 FROM public.tribunal_decisionrevision d
   JOIN public.tribunal_proceeding p ON p.id=d.proceeding_id
   JOIN public.tribunal_case c ON c.id=p.case_id
   JOIN public.tribunal_account signer ON signer.id=(data->>'signer_id')::uuid
   WHERE d.id=(data->>'decision_id')::uuid AND p.status='open' AND c.status='open'
    AND d.type NOT IN ('denied','deferred') AND signer.role='president' AND signer.is_active
    AND NOT EXISTS(SELECT 1 FROM public.tribunal_decisionrevision later WHERE later.proceeding_id=d.proceeding_id AND later.number>d.number)
    AND public.ctm_safe_council_pdf((data->>'signed_file_id')::uuid,c.id)
    AND EXISTS(SELECT 1 FROM public.tribunal_presidentialapproval approval
        WHERE approval.decision_id=d.id AND approval.president_id=signer.id)
    AND EXISTS(SELECT 1 FROM public.tribunal_signatureattestation signature
        WHERE signature.file_id=(data->>'signed_file_id')::uuid AND signature.signer_id=signer.id))
$$;
