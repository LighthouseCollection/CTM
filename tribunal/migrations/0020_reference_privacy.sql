CREATE FUNCTION public.ctm_configuration_safe(data jsonb) RETURNS boolean
LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog,public AS $$
DECLARE entry record; child jsonb;
BEGIN
 IF jsonb_typeof(data)='object' THEN
  FOR entry IN SELECT key,value FROM jsonb_each(data) LOOP
   IF lower(entry.key) IN ('api_key','secret','password','token','private_key','client_secret','webhook_secret') OR NOT public.ctm_configuration_safe(entry.value) THEN RETURN false; END IF;
  END LOOP;
 ELSIF jsonb_typeof(data)='array' THEN
  FOR child IN SELECT value FROM jsonb_array_elements(data) LOOP
   IF NOT public.ctm_configuration_safe(child) THEN RETURN false; END IF;
  END LOOP;
 END IF;
 RETURN true;
END
$$;

CREATE FUNCTION public.ctm_reference_readable(resource text,data jsonb) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
 SELECT public.ctm_actor_role() IS NOT NULL AND CASE resource
  WHEN 'questionnaireversion' THEN data->'published'='true'::jsonb OR public.ctm_actor_role() IN ('admin','secretary')
  WHEN 'reportquestion' THEN public.ctm_is_council()
  WHEN 'settingrevision' THEN public.ctm_actor_role() IN ('admin','secretary')
  ELSE false END
$$;

CREATE FUNCTION public.ctm_reference_writable(resource text,data jsonb) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
 SELECT public.ctm_actor_role() IN ('admin','secretary') AND CASE resource
  WHEN 'questionnaireversion' THEN data->>'purpose' IN ('petition','appeal','medical_release')
   AND jsonb_typeof(data->'definition')='object'
   AND (data->'published'<>'true'::jsonb OR (btrim(data->>'declaration_en')<>'' AND btrim(data->>'declaration_ar')<>''))
  WHEN 'reportquestion' THEN btrim(data->>'code')<>'' AND btrim(data->>'wording_en')<>''
  WHEN 'settingrevision' THEN data->>'actor_id'=public.ctm_actor_id()::text
   AND data->>'key' IN ('translation_prompt','translation_routing','tribunal_contact','email_templates','document_categories','recommended_doctors')
   AND public.ctm_configuration_safe(data->'value')
  ELSE false END
$$;
