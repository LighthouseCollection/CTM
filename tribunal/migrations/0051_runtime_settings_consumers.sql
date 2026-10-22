CREATE FUNCTION public.ctm_runtime_tribunal_contact()
RETURNS TABLE(display text,email text,phone text,address text,setting_version integer)
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
DECLARE config record; value jsonb; python_whitespace text;
BEGIN
 python_whitespace=chr(9)||chr(10)||chr(11)||chr(12)||chr(13)
   ||chr(28)||chr(29)||chr(30)||chr(31)||chr(32)||chr(133)||chr(160)
   ||chr(5760)||chr(8192)||chr(8193)||chr(8194)||chr(8195)||chr(8196)
   ||chr(8197)||chr(8198)||chr(8199)||chr(8200)||chr(8201)||chr(8202)
   ||chr(8232)||chr(8233)||chr(8239)||chr(8287)||chr(12288);
 IF public.ctm_worker_caller() OR public.ctm_actor_role() IS NULL THEN RETURN; END IF;
 SELECT s.number,s.value INTO config FROM public.tribunal_settingrevision s
 WHERE s.key='tribunal_contact' ORDER BY s.number DESC LIMIT 1;
 IF NOT FOUND THEN
  RETURN QUERY SELECT NULL::text,NULL::text,NULL::text,NULL::text,0;
  RETURN;
 END IF;
 value=config.value;
 IF jsonb_typeof(value) IS DISTINCT FROM 'object'
   OR octet_length(value::text)>100000
   OR value-ARRAY['display','email','phone','address']<>'{}'::jsonb
   OR value='{}'::jsonb
   OR (value?'display' AND (jsonb_typeof(value->'display') IS DISTINCT FROM 'string'
     OR length(value->>'display') NOT BETWEEN 1 AND 300
     OR translate(value->>'display',python_whitespace,'')=''))
   OR (value?'email' AND (jsonb_typeof(value->'email') IS DISTINCT FROM 'string'
     OR length(value->>'email') NOT BETWEEN 1 AND 254
     OR value->>'email' !~ '^(".*"|[^[:space:]@]+)@([^[:space:]@]+\.[^[:space:]@]+|localhost|\[[A-Fa-f0-9:.]+\])$'))
   OR (value?'phone' AND (jsonb_typeof(value->'phone') IS DISTINCT FROM 'string'
     OR length(value->>'phone') NOT BETWEEN 1 AND 100
     OR translate(value->>'phone',python_whitespace,'')=''))
   OR (value?'address' AND (jsonb_typeof(value->'address') IS DISTINCT FROM 'string'
     OR length(value->>'address') NOT BETWEEN 1 AND 2000
     OR translate(value->>'address',python_whitespace,'')='')) THEN
  RETURN QUERY SELECT NULL::text,NULL::text,NULL::text,NULL::text,config.number;
  RETURN;
 END IF;
 RETURN QUERY SELECT value->>'display',value->>'email',value->>'phone',value->>'address',config.number;
END $$;
REVOKE ALL ON FUNCTION public.ctm_runtime_tribunal_contact() FROM PUBLIC;

CREATE FUNCTION public.ctm_case_recommended_doctors(case_id uuid,requested_specialty text)
RETURNS TABLE(id uuid,name text,specialty text,contact text,setting_version integer)
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
DECLARE config record; value jsonb; item jsonb; doctor_id uuid;
 python_whitespace text;
 seen_ids uuid[]=ARRAY[]::uuid[]; matched integer;
BEGIN
 python_whitespace=chr(9)||chr(10)||chr(11)||chr(12)||chr(13)
   ||chr(28)||chr(29)||chr(30)||chr(31)||chr(32)||chr(133)||chr(160)
   ||chr(5760)||chr(8192)||chr(8193)||chr(8194)||chr(8195)||chr(8196)
   ||chr(8197)||chr(8198)||chr(8199)||chr(8200)||chr(8201)||chr(8202)
   ||chr(8232)||chr(8233)||chr(8239)||chr(8287)||chr(12288);
 IF public.ctm_worker_caller() OR NOT public.ctm_is_council()
   OR NOT EXISTS(SELECT 1 FROM public.tribunal_case c WHERE c.id=case_id) THEN RETURN; END IF;
 IF requested_specialty IS NULL OR requested_specialty NOT IN ('medical','psychological') THEN
  RAISE EXCEPTION 'Unsupported doctor specialty' USING ERRCODE='22023';
 END IF;
 SELECT s.number,s.value INTO config FROM public.tribunal_settingrevision s
 WHERE s.key='recommended_doctors' ORDER BY s.number DESC LIMIT 1;
 IF NOT FOUND THEN
  RETURN QUERY SELECT NULL::uuid,NULL::text,NULL::text,NULL::text,0;
  RETURN;
 END IF;
 value=config.value;
 IF jsonb_typeof(value) IS DISTINCT FROM 'object'
   OR octet_length(value::text)>100000
   OR value-ARRAY['doctors']<>'{}'::jsonb
   OR jsonb_typeof(value->'doctors') IS DISTINCT FROM 'array' THEN
  RETURN QUERY SELECT NULL::uuid,NULL::text,NULL::text,NULL::text,config.number;
  RETURN;
 END IF;
 FOR item IN SELECT entry FROM jsonb_array_elements(value->'doctors') AS doctors(entry) LOOP
  IF jsonb_typeof(item) IS DISTINCT FROM 'object'
    OR item-ARRAY['id','name','specialty','contact','active']<>'{}'::jsonb
    OR jsonb_typeof(item->'id') IS DISTINCT FROM 'string'
    OR jsonb_typeof(item->'name') IS DISTINCT FROM 'string'
    OR jsonb_typeof(item->'specialty') IS DISTINCT FROM 'string'
    OR jsonb_typeof(item->'contact') IS DISTINCT FROM 'string'
    OR jsonb_typeof(item->'active') IS DISTINCT FROM 'boolean'
    OR length(item->>'id') NOT BETWEEN 1 AND 36
    OR length(item->>'name') NOT BETWEEN 1 AND 300
    OR translate(item->>'name',python_whitespace,'')=''
    OR item->>'specialty' NOT IN ('medical','psychological','both')
    OR length(item->>'contact') NOT BETWEEN 1 AND 2000
    OR translate(item->>'contact',python_whitespace,'')='' THEN
   RETURN QUERY SELECT NULL::uuid,NULL::text,NULL::text,NULL::text,config.number;
   RETURN;
  END IF;
  BEGIN
   doctor_id=(item->>'id')::uuid;
  EXCEPTION WHEN invalid_text_representation THEN
   RETURN QUERY SELECT NULL::uuid,NULL::text,NULL::text,NULL::text,config.number;
   RETURN;
  END;
  IF doctor_id=ANY(seen_ids) THEN
   RETURN QUERY SELECT NULL::uuid,NULL::text,NULL::text,NULL::text,config.number;
   RETURN;
  END IF;
  seen_ids=array_append(seen_ids,doctor_id);
 END LOOP;
 RETURN QUERY SELECT (entry->>'id')::uuid,entry->>'name',entry->>'specialty',entry->>'contact',config.number
 FROM jsonb_array_elements(value->'doctors') WITH ORDINALITY AS doctors(entry,position)
 WHERE (entry->>'active')::boolean AND entry->>'specialty' IN (requested_specialty,'both')
 ORDER BY position;
 GET DIAGNOSTICS matched=ROW_COUNT;
 IF matched=0 THEN
  RETURN QUERY SELECT NULL::uuid,NULL::text,NULL::text,NULL::text,config.number;
 END IF;
END $$;
REVOKE ALL ON FUNCTION public.ctm_case_recommended_doctors(uuid,text) FROM PUBLIC;
