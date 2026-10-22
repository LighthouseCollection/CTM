CREATE FUNCTION public.ctm_assessment_release_metadata(target uuid) RETURNS jsonb
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
 SELECT CASE WHEN public.ctm_is_council() AND EXISTS(SELECT 1 FROM public.tribunal_reportrequest r WHERE r.id=target AND r.kind IN ('medical','psychological')) THEN
  (SELECT jsonb_build_object('release_status',CASE WHEN bool_or(m.scope->'council'='true'::jsonb) THEN 'signed' WHEN count(m.id)>0 THEN 'out_of_scope' ELSE 'none' END,
    'release_scope',CASE WHEN count(m.id)>0 THEN jsonb_build_object('council',coalesce(bool_or(m.scope->'council'='true'::jsonb),false)) ELSE NULL END)
   FROM public.tribunal_reportrequest r JOIN public.tribunal_party p ON p.id=r.subject_id
   LEFT JOIN public.tribunal_medicalrelease m ON m.request_id=r.id AND m.subject_id=p.account_id WHERE r.id=target)
 ELSE '{}'::jsonb END
$$;

CREATE FUNCTION public.ctm_library_readable(resource text,data jsonb) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
 SELECT public.ctm_is_council() AND CASE WHEN resource='reporttemplate' THEN
  (data->>'shared'='true' OR data->>'owner_id'=public.ctm_actor_id()::text OR public.ctm_actor_role() IN ('admin','secretary'))
 ELSE EXISTS(SELECT 1 FROM public.tribunal_reporttemplate t WHERE t.id=(data->>'template_id')::uuid AND
   (t.shared OR t.owner_id=public.ctm_actor_id() OR public.ctm_actor_role() IN ('admin','secretary'))) END
$$;

CREATE FUNCTION public.ctm_library_writable(resource text,data jsonb) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
 SELECT public.ctm_is_council() AND CASE WHEN resource='reporttemplate' THEN
  ((data->>'shared'='true' AND data->>'owner_id' IS NULL AND public.ctm_actor_role() IN ('admin','secretary')) OR
   (data->>'shared'='false' AND data->>'owner_id'=public.ctm_actor_id()::text))
 ELSE data->>'actor_id'=public.ctm_actor_id()::text AND EXISTS(SELECT 1 FROM public.tribunal_reporttemplate t WHERE t.id=(data->>'template_id')::uuid AND NOT t.retired AND
   ((t.shared AND public.ctm_actor_role() IN ('admin','secretary')) OR (NOT t.shared AND t.owner_id=public.ctm_actor_id()))) END
$$;

CREATE FUNCTION public.ctm_preserve_template_identity() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog,public AS $$
BEGIN
 IF (to_jsonb(NEW)-'retired') IS DISTINCT FROM (to_jsonb(OLD)-'retired') OR (OLD.retired AND NOT NEW.retired) THEN
  RAISE EXCEPTION 'Retained template identity and retirement are immutable' USING ERRCODE='42501';
 END IF;
 RETURN NEW;
END
$$;
CREATE TRIGGER preserve_template_identity BEFORE UPDATE ON public.tribunal_reporttemplate FOR EACH ROW EXECUTE FUNCTION public.ctm_preserve_template_identity();
CREATE TRIGGER preserve_template_delete BEFORE DELETE ON public.tribunal_templateversion FOR EACH ROW EXECUTE FUNCTION public.ctm_reject_history_update();
