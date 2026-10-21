CREATE FUNCTION public.ctm_council_visible() RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
 SELECT public.ctm_is_council()
$$;

CREATE FUNCTION public.ctm_council_case_writer(target uuid) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
 SELECT public.ctm_is_council() AND EXISTS(
   SELECT 1 FROM public.tribunal_case c WHERE c.id=target
   AND (public.ctm_actor_role() IN ('admin','secretary') OR c.assigned_member_id=public.ctm_actor_id())
   AND (c.status='open' OR EXISTS(SELECT 1 FROM public.tribunal_application a
       WHERE a.case_id=c.id AND a.kind='appeal' AND a.status='submitted')))
$$;

CREATE FUNCTION public.ctm_council_proceeding_writer(target uuid) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
 SELECT EXISTS(SELECT 1 FROM public.tribunal_proceeding p JOIN public.tribunal_case c ON c.id=p.case_id
   WHERE p.id=target AND p.status='open' AND c.status='open' AND public.ctm_council_case_writer(c.id))
$$;

CREATE FUNCTION public.ctm_council_hearing_writer(target uuid) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
 SELECT EXISTS(SELECT 1 FROM public.tribunal_hearing h
   JOIN public.tribunal_agendaitem a ON a.id=h.agenda_id
   JOIN public.tribunal_councilsession s ON s.id=a.session_id
   JOIN public.tribunal_case c ON c.id=a.case_id
   LEFT JOIN public.tribunal_proceeding p ON p.id=h.proceeding_id
   WHERE h.id=target AND h.state='held'
   AND public.ctm_council_case_writer(c.id)
   AND ((h.proceeding_id IS NOT NULL AND p.case_id=c.id AND p.status='open' AND c.status='open')
     OR (h.proceeding_id IS NULL AND EXISTS(SELECT 1 FROM public.tribunal_application f
          WHERE f.case_id=c.id AND f.kind='appeal' AND f.status='submitted'))))
$$;

CREATE FUNCTION public.ctm_council_writable(resource text,data jsonb,operation text) RETURNS boolean
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
DECLARE actor uuid=public.ctm_actor_id(); role_name text=public.ctm_actor_role();
BEGIN
 IF NOT public.ctm_is_council() THEN RETURN false; END IF;
 CASE resource
 WHEN 'councilsession' THEN
   RETURN role_name IN ('admin','secretary') AND
     ((operation='insert' AND data->>'state'='planned') OR (operation='update' AND data->>'state' IN ('planned','closed')));
 WHEN 'agendaitem' THEN
   RETURN (data->>'part')::integer IN (1,2)
     AND (operation='update' OR data->>'state'='scheduled')
     AND (operation='update' OR (data->>'part')::integer=2 OR role_name IN ('admin','secretary'))
     AND public.ctm_council_case_writer((data->>'case_id')::uuid)
     AND EXISTS(SELECT 1 FROM public.tribunal_councilsession s WHERE s.id=(data->>'session_id')::uuid AND s.state='planned')
     AND (data->>'carried_from_id' IS NULL OR EXISTS(
       SELECT 1 FROM public.tribunal_agendaitem previous
       JOIN public.tribunal_councilsession ps ON ps.id=previous.session_id
       JOIN public.tribunal_councilsession next_session ON next_session.id=(data->>'session_id')::uuid
       WHERE previous.id=(data->>'carried_from_id')::uuid AND previous.case_id=(data->>'case_id')::uuid AND ps.date<next_session.date));
 WHEN 'caseassignment' THEN
   RETURN data->>'actor_id'=actor::text AND role_name IN ('admin','secretary')
     AND EXISTS(SELECT 1 FROM public.tribunal_case c WHERE c.id=(data->>'case_id')::uuid AND c.status='open')
     AND EXISTS(SELECT 1 FROM public.tribunal_account m WHERE m.id=(data->>'member_id')::uuid AND m.is_active AND m.role<>'applicant')
     AND EXISTS(SELECT 1 FROM public.tribunal_account p WHERE p.id=(data->>'president_id')::uuid AND p.is_active AND p.role='president');
 WHEN 'hearing' THEN
   RETURN data->>'presenter_id'=actor::text AND EXISTS(
     SELECT 1 FROM public.tribunal_agendaitem a JOIN public.tribunal_case c ON c.id=a.case_id
     JOIN public.tribunal_councilsession s ON s.id=a.session_id
     WHERE a.id=(data->>'agenda_id')::uuid AND c.assigned_member_id=actor AND a.state='scheduled' AND s.state='planned'
     AND public.ctm_council_case_writer(c.id)
     AND ((data->>'proceeding_id' IS NOT NULL AND EXISTS(SELECT 1 FROM public.tribunal_proceeding p
          WHERE p.id=(data->>'proceeding_id')::uuid AND p.case_id=c.id AND p.status='open' AND c.status='open'))
       OR (data->>'proceeding_id' IS NULL AND EXISTS(SELECT 1 FROM public.tribunal_application f
          WHERE f.case_id=c.id AND f.kind='appeal' AND f.status='submitted'))));
 WHEN 'attendance' THEN
   RETURN data->>'actor_id'=actor::text
     AND EXISTS(SELECT 1 FROM public.tribunal_account m WHERE m.id=(data->>'member_id')::uuid AND m.is_active AND m.role<>'applicant')
     AND EXISTS(SELECT 1 FROM public.tribunal_councilsession s WHERE s.id=(data->>'session_id')::uuid AND s.state='planned')
     AND ((data->>'hearing_id' IS NULL AND role_name IN ('admin','secretary'))
       OR (data->>'hearing_id' IS NOT NULL AND public.ctm_council_hearing_writer((data->>'hearing_id')::uuid)
         AND EXISTS(SELECT 1 FROM public.tribunal_hearing h JOIN public.tribunal_agendaitem a ON a.id=h.agenda_id
           WHERE h.id=(data->>'hearing_id')::uuid AND a.session_id=(data->>'session_id')::uuid
             AND (role_name IN ('admin','secretary') OR (h.presenter_id=actor
               AND current_setting('ctm.hearing_snapshot',true)=h.id::text
               AND NOT EXISTS(SELECT 1 FROM public.tribunal_attendance previous
                 WHERE previous.hearing_id=h.id AND previous.member_id=(data->>'member_id')::uuid))))));
 WHEN 'hearingoutcome' THEN
   RETURN data->>'actor_id'=actor::text AND public.ctm_council_hearing_writer((data->>'hearing_id')::uuid);
 WHEN 'casenote' THEN
   RETURN data->>'author_id'=actor::text AND public.ctm_council_proceeding_writer((data->>'proceeding_id')::uuid);
 WHEN 'noterevision' THEN
   RETURN data->>'actor_id'=actor::text AND EXISTS(SELECT 1 FROM public.tribunal_casenote n
     WHERE n.id=(data->>'note_id')::uuid AND n.author_id=actor AND public.ctm_council_proceeding_writer(n.proceeding_id));
 WHEN 'findingrevision' THEN
   RETURN data->>'actor_id'=actor::text AND public.ctm_council_proceeding_writer((data->>'proceeding_id')::uuid);
 ELSE RETURN false;
 END CASE;
END $$;

CREATE FUNCTION public.ctm_council_mutable(resource text,data jsonb) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
 SELECT CASE WHEN resource='councilsession' THEN
   public.ctm_is_council()
 WHEN resource='agendaitem' THEN public.ctm_council_writable(resource,data,'update')
 ELSE false END
$$;

CREATE FUNCTION public.ctm_preserve_council_context() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog,public AS $$
BEGIN
 IF TG_TABLE_NAME='tribunal_agendaitem' THEN
   IF NEW.case_id IS DISTINCT FROM OLD.case_id OR NEW.session_id IS DISTINCT FROM OLD.session_id OR NEW.part IS DISTINCT FROM OLD.part THEN
     RAISE EXCEPTION 'Agenda context is immutable; use explicit placement history';
   END IF;
 ELSIF TG_TABLE_NAME='tribunal_councilsession' THEN
   IF OLD.state='closed' THEN
     RAISE EXCEPTION 'Closed council session is read-only';
   END IF;
   IF NEW.date IS DISTINCT FROM OLD.date THEN
     RAISE EXCEPTION 'Rescheduling requires a new dated council session';
   END IF;
 END IF;
 RETURN NEW;
END $$;

CREATE TRIGGER preserve_council_context BEFORE UPDATE ON public.tribunal_agendaitem
FOR EACH ROW EXECUTE FUNCTION public.ctm_preserve_council_context();
CREATE TRIGGER preserve_council_context BEFORE UPDATE ON public.tribunal_councilsession
FOR EACH ROW EXECUTE FUNCTION public.ctm_preserve_council_context();
