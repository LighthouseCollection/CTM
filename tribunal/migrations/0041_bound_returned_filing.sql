CREATE OR REPLACE FUNCTION public.ctm_filing_case(target uuid) RETURNS boolean
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
DECLARE answers jsonb; own_dob date; spouse_dob date; married date;
BEGIN
 IF public.ctm_filing_application() IS NOT NULL AND target=public.ctm_context_uuid('ctm.filing_created_case') THEN RETURN true; END IF;
 IF EXISTS(SELECT 1 FROM public.tribunal_application a
 JOIN public.tribunal_account owner ON owner.id=a.owner_id
 JOIN public.tribunal_party party ON party.id=a.party_id AND party.case_id=a.case_id
   AND party.account_id=a.owner_id AND party.person_id=owner.person_id
 JOIN public.tribunal_case c ON c.id=a.case_id AND c.status='open'
 JOIN public.tribunal_proceeding p ON p.id=a.proceeding_id AND p.case_id=c.id AND p.status='open'
 WHERE a.id=public.ctm_filing_application() AND a.case_id=target
   AND a.kind='petition' AND a.status='returned' AND a.submitted_at IS NOT NULL
   AND EXISTS(SELECT 1 FROM public.tribunal_submission s WHERE s.application_id=a.id AND s.actor_id=a.owner_id)
 ) THEN RETURN true; END IF;
 SELECT r.answers INTO answers FROM public.tribunal_application a JOIN public.tribunal_answerrevision r
 ON r.application_id=a.id AND r.number=a.current_version WHERE a.id=public.ctm_filing_application();
 IF answers IS NULL THEN RETURN false; END IF;
 own_dob=(answers->>'birth_date')::date; spouse_dob=nullif(answers->>'spouse_birth_date','')::date; married=(answers->>'marriage_date')::date;
 IF spouse_dob IS NULL THEN RETURN false; END IF;
 RETURN EXISTS(SELECT 1 FROM public.tribunal_case c WHERE c.id=target AND c.marriage_date=married
 AND c.spouse_dob_low=least(own_dob,spouse_dob) AND c.spouse_dob_high=greatest(own_dob,spouse_dob));
EXCEPTION WHEN invalid_datetime_format OR datetime_field_overflow THEN RETURN false;
END $$;
