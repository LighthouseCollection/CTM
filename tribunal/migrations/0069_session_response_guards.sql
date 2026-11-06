-- #116 / D-0036: council session attendance answers and the .ics SEQUENCE.

-- Who can read an answer: the member who gave it (while an active council
-- account), and secretary, president or admin. Applicants and the worker get nothing.
CREATE FUNCTION public.ctm_session_response_readable(data jsonb) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
 SELECT NOT public.ctm_worker_caller() AND (
   public.ctm_actor_role() IN ('secretary','president','admin')
   OR (public.ctm_actor_role()='member' AND data->>'member_id'=public.ctm_actor_id()::text))
$$;

-- Who can add an answer: an active council account, for themself only, while
-- the session is planned and its start time is still ahead.
CREATE FUNCTION public.ctm_session_response_writable(data jsonb) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
 SELECT NOT public.ctm_worker_caller()
   AND public.ctm_actor_role() IN ('member','president','secretary','admin')
   AND data->>'member_id'=public.ctm_actor_id()::text
   AND data->>'answer' IN ('attend','not_attend')
   AND EXISTS(SELECT 1 FROM public.tribunal_councilsession s
     WHERE s.id=(data->>'session_id')::uuid AND s.state='planned'
       AND s.starts_at IS NOT NULL AND s.starts_at>clock_timestamp())
$$;

-- The answer time is the database clock, so "the latest answer counts" cannot
-- be reordered by a caller-supplied created_at.
CREATE FUNCTION public.ctm_session_response_stamp() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public AS $$
BEGIN
 IF NOT public.ctm_migration_caller() THEN NEW.created_at=clock_timestamp(); END IF;
 RETURN NEW;
END $$;

-- Answers are never changed. They are removed only with their session during an
-- authorized planned reschedule (as attendance is, 0016) or an admin purge.
CREATE FUNCTION public.ctm_guard_session_response_history() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public AS $$
BEGIN
 IF TG_OP='DELETE' AND (public.ctm_admin_case_purge_active() OR public.ctm_session_transfer_context(OLD.session_id)) THEN
  RETURN OLD;
 END IF;
 RAISE EXCEPTION 'CTM historical records cannot be overwritten' USING ERRCODE='23514';
END $$;

-- RFC 5545: a calendar file's SEQUENCE only goes up.
CREATE FUNCTION public.ctm_session_ics_sequence_rises() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public AS $$
BEGIN
 IF NEW.ics_sequence<OLD.ics_sequence THEN
  RAISE EXCEPTION 'A calendar sequence cannot go down' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$;
