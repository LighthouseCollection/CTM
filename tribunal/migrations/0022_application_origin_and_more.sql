CREATE FUNCTION public.ctm_guard_closed_intake() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public AS $$
DECLARE app public.tribunal_application;
BEGIN
 IF TG_TABLE_NAME='tribunal_application' THEN
  IF TG_OP='UPDATE' AND OLD.id::text=current_setting('ctm.council_result',true)
    AND (to_jsonb(NEW)-'status') IS DISTINCT FROM (to_jsonb(OLD)-'status') THEN
   RAISE EXCEPTION 'Council result context permits only the filing status transition' USING ERRCODE='42501';
  END IF;
  IF TG_OP='UPDATE' AND OLD.origin IS DISTINCT FROM NEW.origin AND (OLD.submitted_at IS NOT NULL OR OLD.origin='closed_case_intake') THEN
   RAISE EXCEPTION 'Filing origin is retained' USING ERRCODE='42501';
  END IF;
  IF NEW.origin<>'closed_case_intake' THEN RETURN NEW; END IF;
  IF NEW.kind<>'petition' OR NEW.proceeding_id IS NOT NULL OR NOT EXISTS(SELECT 1 FROM public.tribunal_party p
   JOIN public.tribunal_account a ON a.id=NEW.owner_id WHERE p.case_id=NEW.case_id AND p.account_id=a.id AND p.person_id=a.person_id
    AND (NEW.party_id IS NULL OR NEW.party_id=p.id)) THEN
   RAISE EXCEPTION 'Closed-case intake requires a retained linked spouse and no original proceeding write' USING ERRCODE='42501';
  END IF;
  IF (TG_OP='INSERT' OR OLD.origin IS DISTINCT FROM NEW.origin) AND NOT EXISTS(SELECT 1 FROM public.tribunal_case c WHERE c.id=NEW.case_id AND c.status='closed') THEN
   RAISE EXCEPTION 'Closed intake must originate against a closed case' USING ERRCODE='42501';
  END IF;
  IF EXISTS(SELECT 1 FROM public.tribunal_application a WHERE a.owner_id=NEW.owner_id AND a.case_id=NEW.case_id AND a.kind='petition' AND a.submitted_at IS NOT NULL AND a.id<>NEW.id) THEN
   RAISE EXCEPTION 'An existing filer must use the appeal route' USING ERRCODE='42501';
  END IF;
  IF NEW.submitted_at IS NOT NULL AND (NEW.party_id IS NULL OR NOT EXISTS(SELECT 1 FROM public.tribunal_submission sub WHERE sub.application_id=NEW.id)) THEN
   RAISE EXCEPTION 'A formal closed intake requires its linked spouse and retained submission' USING ERRCODE='42501';
  END IF;
  IF NEW.status IN ('accepted','declined') AND NOT EXISTS(SELECT 1 FROM public.tribunal_appealdisposition d WHERE d.application_id=NEW.id AND d.result=CASE WHEN NEW.status='accepted' THEN 'accept' ELSE 'decline' END) THEN
   RAISE EXCEPTION 'Council result must precede concluded intake status' USING ERRCODE='42501';
  END IF;
  IF TG_OP='UPDATE' AND OLD.status IN ('accepted','declined','withdrawn') AND NEW.status<>OLD.status
    AND NOT (OLD.status='accepted' AND NEW.status='withdrawn') THEN
   RAISE EXCEPTION 'Concluded intake cannot be reset to pending' USING ERRCODE='42501';
  END IF;
  IF TG_OP='UPDATE' AND OLD.submitted_at IS NOT NULL AND NEW.current_version<>OLD.current_version THEN
   RAISE EXCEPTION 'Submitted intake answers are retained' USING ERRCODE='42501';
  END IF;
 ELSE
  IF TG_TABLE_NAME IN ('tribunal_answerrevision','tribunal_submission') THEN
   SELECT * INTO app FROM public.tribunal_application WHERE id=NEW.application_id;
  ELSIF TG_TABLE_NAME='tribunal_fileversion' THEN
   SELECT a.* INTO app FROM public.tribunal_application a JOIN public.tribunal_attachment f ON f.application_id=a.id WHERE f.id=NEW.attachment_id;
  END IF;
  IF app.origin='closed_case_intake' THEN
   IF TG_TABLE_NAME='tribunal_answerrevision' THEN
    IF app.submitted_at IS NOT NULL THEN
     RAISE EXCEPTION 'Append new information instead of overwriting submitted intake' USING ERRCODE='42501';
    END IF;
   ELSIF TG_TABLE_NAME='tribunal_submission' THEN
    IF app.submitted_at IS NOT NULL OR EXISTS(SELECT 1 FROM public.tribunal_submission sub WHERE sub.application_id=app.id) THEN
     RAISE EXCEPTION 'Closed intake has exactly one formal submission' USING ERRCODE='42501';
    END IF;
    IF NOT EXISTS(SELECT 1 FROM public.tribunal_answerrevision r WHERE r.id=NEW.revision_id AND r.application_id=app.id AND r.number=app.current_version AND jsonb_typeof(r.answers->'new_information')='string' AND btrim(r.answers->>'new_information')<>'') OR NOT EXISTS(SELECT 1 FROM public.tribunal_feeobligation f WHERE f.application_id=app.id AND f.status IN ('paid','waived','historical_exempt')) THEN
     RAISE EXCEPTION 'Closed intake requires frozen new information and satisfied filing fee' USING ERRCODE='42501';
    END IF;
   ELSIF TG_TABLE_NAME='tribunal_fileversion' THEN
    IF app.status NOT IN ('draft','submitted') THEN
     RAISE EXCEPTION 'Concluded intake cannot accept file versions' USING ERRCODE='42501';
    END IF;
   END IF;
  END IF;
 END IF;
 RETURN NEW;
END
$$;

CREATE FUNCTION public.ctm_council_result_allowed(target uuid,hearing_id uuid,choice text) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
 SELECT target::text=current_setting('ctm.council_result',true)
  AND hearing_id::text=current_setting('ctm.result_hearing',true) AND choice=current_setting('ctm.result_choice',true)
  AND choice IN ('accept','decline') AND public.ctm_is_council()
  AND EXISTS(SELECT 1 FROM public.tribunal_application a JOIN public.tribunal_case c ON c.id=a.case_id
   JOIN public.tribunal_hearing h ON h.id=hearing_id JOIN public.tribunal_agendaitem agenda ON agenda.id=h.agenda_id
   WHERE a.id=target AND a.status='submitted' AND (a.kind='appeal' OR a.origin='closed_case_intake')
    AND (public.ctm_actor_role() IN ('admin','secretary') OR c.assigned_member_id=public.ctm_actor_id())
    AND agenda.case_id=c.id AND agenda.part=2 AND h.state='held' AND h.presenter_id=c.assigned_member_id
    AND (a.origin<>'closed_case_intake' OR (h.created_at>=a.submitted_at AND (choice='decline' OR EXISTS(
     SELECT 1 FROM public.tribunal_submission s JOIN public.tribunal_answerrevision r ON r.id=s.revision_id
     WHERE s.application_id=a.id AND jsonb_typeof(r.answers->'new_information')='string' AND btrim(r.answers->>'new_information')<>'')))))
$$;

CREATE FUNCTION public.ctm_council_result_update(data jsonb) RETURNS boolean
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
DECLARE choice text=current_setting('ctm.result_choice',true); context_hearing uuid;
BEGIN
 BEGIN context_hearing=current_setting('ctm.result_hearing',true)::uuid; EXCEPTION WHEN invalid_text_representation THEN RETURN false; END;
 IF public.ctm_council_result_allowed((data->>'id')::uuid,context_hearing,choice) IS NOT TRUE THEN RETURN false; END IF;
 IF data->>'status'='submitted' THEN RETURN true; END IF;
 RETURN data->>'status'=CASE WHEN choice='accept' THEN 'accepted' ELSE 'declined' END AND EXISTS(
  SELECT 1 FROM public.tribunal_appealdisposition d WHERE d.application_id=(data->>'id')::uuid
   AND d.hearing_id=context_hearing AND d.result=choice AND d.actor_id=public.ctm_actor_id());
END
$$;

CREATE FUNCTION public.ctm_reconsideration_readable(data jsonb) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
 SELECT public.ctm_is_council() OR EXISTS(SELECT 1 FROM public.tribunal_application a
  WHERE a.id=(data->>'application_id')::uuid AND a.owner_id=public.ctm_actor_id() AND public.ctm_actor_role()='applicant')
$$;

CREATE FUNCTION public.ctm_reconsideration_writable(resource text,data jsonb) RETURNS boolean
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
DECLARE app public.tribunal_application;
BEGIN
 SELECT * INTO app FROM public.tribunal_application WHERE id=(data->>'application_id')::uuid;
 IF data->>'actor_id' IS DISTINCT FROM public.ctm_actor_id()::text OR app.status<>'submitted'
  OR NOT (app.kind='appeal' OR app.origin='closed_case_intake') THEN RETURN false; END IF;
 IF resource='appealsupplement' THEN
  RETURN public.ctm_actor_role()='applicant' AND app.owner_id=public.ctm_actor_id()
   AND (btrim(coalesce(data->>'text',''))<>'' OR jsonb_array_length(data->'manifest')>0)
   AND NOT EXISTS(SELECT 1 FROM public.tribunal_appealdisposition d WHERE d.application_id=app.id)
   AND NOT EXISTS(SELECT 1 FROM jsonb_array_elements(data->'manifest') item WHERE NOT EXISTS(
    SELECT 1 FROM public.tribunal_fileversion v JOIN public.tribunal_attachment a ON a.id=v.attachment_id
     WHERE v.id::text=item->>'id' AND v.sha256=item->>'sha256' AND a.application_id=app.id AND a.owner_id=app.owner_id
      AND (SELECT e.result FROM public.tribunal_filetechnicalevent e WHERE e.file_id=v.id AND e.task='scan' ORDER BY e.created_at DESC,e.id DESC LIMIT 1)='clean'));
 END IF;
 IF public.ctm_council_result_allowed(app.id,(data->>'hearing_id')::uuid,data->>'result') IS NOT TRUE THEN RETURN false; END IF;
 IF data->>'result'='decline' THEN RETURN data->>'reopened_proceeding_id' IS NULL; END IF;
 RETURN EXISTS(SELECT 1 FROM public.tribunal_proceeding p JOIN public.tribunal_case c ON c.id=p.case_id
   WHERE p.id=(data->>'reopened_proceeding_id')::uuid AND p.case_id=app.case_id AND p.status='open' AND c.status='open')
  AND EXISTS(SELECT 1 FROM public.tribunal_party own_party JOIN public.tribunal_opencaseclaim own_claim ON own_claim.person_id=own_party.person_id AND own_claim.case_id=own_party.case_id
   WHERE own_party.case_id=app.case_id AND own_party.account_id=app.owner_id AND own_party.participating AND own_party.withdrawn_at IS NULL)
  AND NOT EXISTS(SELECT 1 FROM public.tribunal_party party WHERE party.case_id=app.case_id AND party.participating AND party.person_id IS NOT NULL AND party.account_id IS NOT NULL
   AND NOT EXISTS(SELECT 1 FROM public.tribunal_opencaseclaim claim WHERE claim.person_id=party.person_id AND claim.case_id=app.case_id));
END
$$;
