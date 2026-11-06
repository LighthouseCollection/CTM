-- #116 / D-0036: council session emails (invite, update, cancel, reminder) in the
-- Outbox, without a Notification row, and the worker's delivery check.

-- Who may queue one: admin or secretary (also president for reminders), for an
-- active, verified council recipient, for an existing planned session at its
-- current calendar sequence, with the key the service builds. The Outbox guard
-- (0037) has already set queued_by_id to the actor.
CREATE FUNCTION public.ctm_session_notice_allowed(data jsonb) RETURNS boolean
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
DECLARE
 actor uuid=public.ctm_actor_id();
 role_name text=public.ctm_actor_role();
 kind text=data->>'kind';
 payload jsonb=data->'payload';
 manual boolean;
 session public.tribunal_councilsession;
 sequence integer;
BEGIN
 IF actor IS NULL OR data->>'queued_by_id' IS DISTINCT FROM actor::text OR data->>'case_id' IS NOT NULL
    OR kind IS NULL OR kind NOT IN ('session_invite','session_update','session_cancel','session_reminder')
    OR role_name IS NULL OR NOT (role_name IN ('admin','secretary') OR (role_name='president' AND kind='session_reminder'))
    OR jsonb_typeof(payload) IS DISTINCT FROM 'object' OR jsonb_typeof(payload->'sequence') IS DISTINCT FROM 'number' THEN
  RETURN false;
 END IF;
 manual=coalesce(payload->'manual'='true'::jsonb,false);
 IF manual AND kind<>'session_reminder' THEN RETURN false; END IF;
 sequence=(payload->>'sequence')::integer;
 SELECT * INTO session FROM public.tribunal_councilsession s WHERE s.id::text=payload->>'session';
 IF NOT FOUND OR session.state<>'planned' OR session.starts_at IS NULL OR session.ics_sequence<>sequence THEN
  RETURN false;
 END IF;
 IF NOT EXISTS(SELECT 1 FROM public.tribunal_account a WHERE a.id::text=data->>'recipient_id' AND a.is_active
     AND a.email_verified AND a.role IN ('member','president','secretary','admin')) THEN
  RETURN false;
 END IF;
 IF manual THEN
  RETURN data->>'key' ~ ('^session_reminder:' || session.id::text || ':now:[0-9]{10}:' || (data->>'recipient_id') || '$');
 END IF;
 RETURN data->>'key' = kind || ':' || session.id::text || ':' || sequence::text || ':' || (data->>'recipient_id');
EXCEPTION WHEN invalid_text_representation OR numeric_value_out_of_range THEN RETURN false;
END $$;

-- The president may read session reminder rows (for the once-an-hour limit).
-- Admin and secretary already read every Outbox row (0037).
CREATE FUNCTION public.ctm_session_reminder_readable(data jsonb) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
 SELECT coalesce(public.ctm_actor_role()='president' AND data->>'kind'='session_reminder'
   AND data->>'case_id' IS NULL AND data->'payload' ? 'session', false)
$$;

-- Worker only: is this queued session email still right to send?
CREATE FUNCTION public.ctm_session_delivery_current(target uuid) RETURNS boolean
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
DECLARE job public.tribunal_outbox; session public.tribunal_councilsession; sequence integer;
BEGIN
 IF NOT public.ctm_worker_caller() AND NOT public.ctm_migration_caller() THEN
  RAISE EXCEPTION 'Worker only' USING ERRCODE='42501';
 END IF;
 SELECT * INTO job FROM public.tribunal_outbox o WHERE o.id=target
   AND o.kind IN ('session_invite','session_update','session_cancel','session_reminder');
 IF NOT FOUND THEN RETURN false; END IF;
 BEGIN
  sequence=(job.payload->>'sequence')::integer;
  SELECT * INTO session FROM public.tribunal_councilsession s WHERE s.id=(job.payload->>'session')::uuid;
 EXCEPTION WHEN invalid_text_representation OR numeric_value_out_of_range THEN RETURN false;
 END;
 IF job.kind='session_cancel' THEN
  -- A moved session is deleted after its cancel is queued; the cancel still goes out.
  RETURN session.id IS NULL OR session.ics_sequence IS NOT DISTINCT FROM sequence;
 END IF;
 IF session.id IS NULL OR session.state<>'planned' OR session.starts_at IS NULL
    OR session.starts_at<=clock_timestamp() OR session.ics_sequence IS DISTINCT FROM sequence THEN
  RETURN false;
 END IF;
 IF job.kind='session_reminder' THEN
  RETURN NOT EXISTS(SELECT 1 FROM public.tribunal_sessionresponse r
    WHERE r.session_id=session.id AND r.member_id=job.recipient_id);
 END IF;
 RETURN true;
END $$;
