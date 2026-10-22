CREATE FUNCTION public.ctm_document_category_labels()
RETURNS TABLE(code text,label_en text,label_ar text,setting_version integer)
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
DECLARE config record; item jsonb; seen text[]=ARRAY[]::text[];
BEGIN
 IF public.ctm_worker_caller() OR public.ctm_actor_role() IS NULL THEN RETURN; END IF;
 SELECT s.number,s.value INTO config FROM public.tribunal_settingrevision s
 WHERE s.key='document_categories' ORDER BY s.number DESC LIMIT 1;
 IF NOT FOUND THEN RETURN; END IF;
 IF jsonb_typeof(config.value) IS DISTINCT FROM 'object' THEN RETURN; END IF;
 IF config.value-'categories'<>'{}'::jsonb
   OR jsonb_typeof(config.value->'categories') IS DISTINCT FROM 'array'
   OR octet_length(config.value::text)>100000 THEN RETURN; END IF;
 FOR item IN SELECT value FROM jsonb_array_elements(config.value->'categories') LOOP
  IF jsonb_typeof(item) IS DISTINCT FROM 'object' THEN RETURN; END IF;
  IF item-ARRAY['code','label_en','label_ar']<>'{}'::jsonb
    OR jsonb_typeof(item->'code') IS DISTINCT FROM 'string'
    OR jsonb_typeof(item->'label_en') IS DISTINCT FROM 'string'
    OR jsonb_typeof(item->'label_ar') IS DISTINCT FROM 'string' THEN RETURN; END IF;
  IF item->>'code' NOT IN ('MC','CMC','CDD','PHOTO','SPOUSE_PHOTO','PET','RO')
    OR item->>'code'=ANY(seen) OR length(item->>'label_en') NOT BETWEEN 1 AND 300
    OR length(item->>'label_ar') NOT BETWEEN 1 AND 300
    OR item->>'label_en' !~ '[^[:space:]]' OR item->>'label_ar' !~ '[^[:space:]]' THEN RETURN; END IF;
  seen=array_append(seen,item->>'code');
 END LOOP;
 RETURN QUERY SELECT entry->>'code',entry->>'label_en',entry->>'label_ar',config.number
 FROM jsonb_array_elements(config.value->'categories') AS categories(entry);
END $$;
REVOKE ALL ON FUNCTION public.ctm_document_category_labels() FROM PUBLIC;
