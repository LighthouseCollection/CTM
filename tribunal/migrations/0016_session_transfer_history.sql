CREATE FUNCTION public.ctm_session_transfer_context(target uuid) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
 SELECT coalesce(public.ctm_actor_role() IN ('admin','secretary'),false) AND EXISTS(
  SELECT 1 FROM public.tribunal_councilsession source,public.tribunal_councilsession destination
  WHERE source.id=target AND source.id::text=current_setting('ctm.reschedule_source',true)
    AND destination.id::text=current_setting('ctm.reschedule_target',true)
    AND source.id<>destination.id AND source.date<>destination.date
    AND source.state='planned' AND destination.state='planned'
    AND NOT EXISTS(SELECT 1 FROM public.tribunal_hearing h JOIN public.tribunal_agendaitem a ON a.id=h.agenda_id WHERE a.session_id=source.id)
    AND NOT EXISTS(SELECT 1 FROM public.agenda_transfer_events transfer WHERE transfer.to_session_id=source.id))
$$;

CREATE FUNCTION public.ctm_testimony_readable(resource text,data jsonb) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
 SELECT public.ctm_is_council() OR EXISTS(SELECT 1 FROM public.tribunal_testimonyappointment appointment
   JOIN public.tribunal_party party ON party.id=appointment.party_id
   WHERE appointment.id=CASE WHEN resource='testimonyappointment' THEN (data->>'id')::uuid ELSE (data->>'appointment_id')::uuid END
     AND public.ctm_actor_role()='applicant' AND party.account_id=public.ctm_actor_id())
$$;

CREATE FUNCTION public.ctm_testimony_writable(resource text,data jsonb) RETURNS boolean
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
DECLARE actor uuid=public.ctm_actor_id(); role_name text=public.ctm_actor_role();
BEGIN
 CASE resource
 WHEN 'testimonyappointment' THEN
   RETURN EXISTS(SELECT 1 FROM public.tribunal_agendaitem a
     JOIN public.tribunal_councilsession s ON s.id=a.session_id
     JOIN public.tribunal_party party ON party.id=(data->>'party_id')::uuid AND party.case_id=a.case_id
     WHERE a.id=(data->>'agenda_id')::uuid AND party.account_id IS NOT NULL AND s.state='planned'
       AND public.ctm_council_case_writer(a.case_id) AND data->>'state' IN ('invited','cancelled')
       AND (data->>'starts_at')::timestamptz < (data->>'ends_at')::timestamptz
       AND (data->>'state'='cancelled' OR (((data->>'starts_at')::timestamptz AT TIME ZONE 'America/Los_Angeles')::date=s.date
         AND ((data->>'ends_at')::timestamptz AT TIME ZONE 'America/Los_Angeles')::date=s.date)));
 WHEN 'appointmentresponse' THEN
   RETURN role_name='applicant' AND data->>'actor_id'=actor::text AND data->>'response' IN ('confirm','reject')
     AND EXISTS(SELECT 1 FROM public.tribunal_testimonyappointment appointment
       JOIN public.tribunal_party party ON party.id=appointment.party_id
       JOIN public.tribunal_agendaitem a ON a.id=appointment.agenda_id
       JOIN public.tribunal_councilsession s ON s.id=a.session_id
       WHERE appointment.id=(data->>'appointment_id')::uuid AND appointment.version=(data->>'version')::integer
         AND party.account_id=actor AND appointment.state<>'cancelled' AND s.state='planned');
 WHEN 'testimonyappointmentversion' THEN
   RETURN data->>'actor_id'=actor::text AND EXISTS(SELECT 1 FROM public.tribunal_testimonyappointment appointment
     JOIN public.tribunal_agendaitem a ON a.id=appointment.agenda_id
     WHERE appointment.id=(data->>'appointment_id')::uuid AND appointment.version=(data->>'version')::integer
       AND public.ctm_council_case_writer(a.case_id) AND appointment.starts_at=(data->>'starts_at')::timestamptz
       AND appointment.ends_at=(data->>'ends_at')::timestamptz AND appointment.instructions=data->>'instructions'
       AND (appointment.state='cancelled')=(data->>'cancelled')::boolean);
 WHEN 'agendatransferevent' THEN
   RETURN data->>'actor_id'=actor::text AND btrim(data->>'reason')<>''
     AND public.ctm_session_transfer_context((data->'from_session_snapshot'->>'id')::uuid)
     AND data->>'to_session_id'=current_setting('ctm.reschedule_target',true)
     AND EXISTS(SELECT 1 FROM public.tribunal_agendaitem a WHERE a.id=(data->>'destination_item_id')::uuid
       AND a.session_id=(data->>'to_session_id')::uuid AND a.case_id=(data->>'case_id')::uuid);
 ELSE RETURN false;
 END CASE;
END $$;

CREATE FUNCTION public.ctm_testimony_delivery_valid(target uuid,expected_version integer,recipient uuid) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
 SELECT EXISTS(SELECT 1 FROM public.tribunal_testimonyappointment appointment
   JOIN public.tribunal_party party ON party.id=appointment.party_id
   JOIN public.tribunal_account account ON account.id=party.account_id
   JOIN public.tribunal_agendaitem a ON a.id=appointment.agenda_id
   JOIN public.tribunal_councilsession s ON s.id=a.session_id
   WHERE appointment.id=target AND appointment.version=expected_version AND appointment.state<>'cancelled'
     AND party.account_id=recipient AND account.is_active AND s.state='planned')
$$;

CREATE FUNCTION public.ctm_session_delivery_closed(target uuid) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
 SELECT EXISTS(SELECT 1 FROM public.tribunal_councilsession s WHERE s.id=target AND s.state='closed')
$$;

CREATE FUNCTION public.ctm_invitation_context(target uuid) RETURNS TABLE(case_id uuid,session_date date,session_planned boolean)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
 SELECT party.case_id,s.date,s.state='planned'
 FROM public.tribunal_testimonyappointment appointment
 JOIN public.tribunal_party party ON party.id=appointment.party_id
 JOIN public.tribunal_agendaitem a ON a.id=appointment.agenda_id
 JOIN public.tribunal_councilsession s ON s.id=a.session_id
 WHERE appointment.id=target AND public.ctm_actor_role()='applicant' AND party.account_id=public.ctm_actor_id()
$$;

CREATE FUNCTION public.ctm_guard_attendance_transfer_delete() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public AS $$
BEGIN
 IF OLD.hearing_id IS NOT NULL OR NOT public.ctm_session_transfer_context(OLD.session_id) THEN
   RAISE EXCEPTION 'Attendance history cannot be deleted outside planned reschedule' USING ERRCODE='23514';
 END IF;
 RETURN OLD;
END $$;

CREATE FUNCTION public.ctm_guard_message_session_transfer() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public AS $$
DECLARE original jsonb;
BEGIN
 SELECT jsonb_build_object('id',s.id::text,'date',s.date::text,'reference','CS'||to_char(s.date,'YYYYMMDD')) INTO original
   FROM public.tribunal_councilsession s WHERE s.id=OLD.session_id;
 IF NOT public.ctm_session_transfer_context(OLD.session_id)
   OR NEW.session_id::text IS DISTINCT FROM current_setting('ctm.reschedule_target',true)
   OR (to_jsonb(NEW)-'session_id'-'session_snapshot') IS DISTINCT FROM (to_jsonb(OLD)-'session_id'-'session_snapshot')
   OR NEW.session_snapshot IS DISTINCT FROM (CASE WHEN OLD.session_snapshot='{}'::jsonb THEN original ELSE OLD.session_snapshot END) THEN
   RAISE EXCEPTION 'Message content/history is immutable; only audited session rebinding is allowed' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$;

DROP TRIGGER immutable_update ON public.tribunal_message;
CREATE TRIGGER immutable_update BEFORE UPDATE ON public.tribunal_message
 FOR EACH ROW EXECUTE FUNCTION public.ctm_guard_message_session_transfer();
DROP TRIGGER preserve_history ON public.tribunal_attendance;
CREATE TRIGGER preserve_history BEFORE DELETE ON public.tribunal_attendance
 FOR EACH ROW EXECUTE FUNCTION public.ctm_guard_attendance_transfer_delete();

CREATE POLICY session_transfer_delete ON public.tribunal_councilsession FOR DELETE
 USING (public.ctm_session_transfer_context(id));
CREATE POLICY session_transfer_delete ON public.tribunal_agendaitem FOR DELETE
 USING (public.ctm_session_transfer_context(session_id));
CREATE POLICY session_transfer_delete ON public.tribunal_attendance FOR DELETE
 USING (hearing_id IS NULL AND public.ctm_session_transfer_context(session_id));
CREATE POLICY session_transfer_update ON public.tribunal_message FOR UPDATE
 USING (public.ctm_session_transfer_context(session_id))
 WITH CHECK (session_id::text=current_setting('ctm.reschedule_target',true)
   AND public.ctm_session_transfer_context(nullif(current_setting('ctm.reschedule_source',true),'')::uuid));

CREATE FUNCTION public.ctm_guard_testimony_context() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public AS $$
BEGIN
 IF NEW.id IS DISTINCT FROM OLD.id OR NEW.created_at IS DISTINCT FROM OLD.created_at
   OR NEW.party_id IS DISTINCT FROM OLD.party_id OR NEW.version<OLD.version OR NEW.version>OLD.version+1 THEN
   RAISE EXCEPTION 'Testimony subject/version cannot be rewritten' USING ERRCODE='23514';
 END IF;
 IF (to_jsonb(NEW)-'agenda_id') IS DISTINCT FROM (to_jsonb(OLD)-'agenda_id') AND NEW.version=OLD.version THEN
   RAISE EXCEPTION 'Testimony changes require a new invitation version' USING ERRCODE='23514';
 END IF;
 IF NEW.agenda_id IS DISTINCT FROM OLD.agenda_id AND NOT EXISTS(
   SELECT 1 FROM public.tribunal_agendaitem old_item,public.tribunal_agendaitem new_item
   WHERE old_item.id=OLD.agenda_id AND new_item.id=NEW.agenda_id AND old_item.case_id=new_item.case_id
     AND public.ctm_session_transfer_context(old_item.session_id)
     AND new_item.session_id::text=current_setting('ctm.reschedule_target',true)) THEN
   RAISE EXCEPTION 'Testimony agenda transfer requires an audited reschedule' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER preserve_testimony_context BEFORE UPDATE ON public.tribunal_testimonyappointment
 FOR EACH ROW EXECUTE FUNCTION public.ctm_guard_testimony_context();

CREATE FUNCTION public.ctm_guard_testimony_overlap() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public AS $$
DECLARE target uuid;
BEGIN
 SELECT session_id INTO target FROM public.tribunal_agendaitem WHERE id=NEW.agenda_id;
 PERFORM 1 FROM public.tribunal_councilsession WHERE id=target FOR UPDATE;
 IF NEW.state<>'cancelled' AND EXISTS(SELECT 1 FROM public.tribunal_testimonyappointment other
   JOIN public.tribunal_agendaitem a ON a.id=other.agenda_id
   WHERE a.session_id=target AND other.id<>NEW.id AND other.state<>'cancelled'
     AND other.starts_at<NEW.ends_at AND other.ends_at>NEW.starts_at) THEN
   RAISE EXCEPTION 'Testimony appointments may not overlap' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER testimony_overlap BEFORE INSERT OR UPDATE ON public.tribunal_testimonyappointment
 FOR EACH ROW EXECUTE FUNCTION public.ctm_guard_testimony_overlap();
