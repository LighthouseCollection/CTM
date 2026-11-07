-- #175 / D-0043: council seats separate from the system role.

-- The current seat: the latest recorded change, or the role default when none
-- is recorded (member and president: voting seat; secretary and admin: none).
-- An inactive account or an applicant never holds a seat.
CREATE FUNCTION public.ctm_council_seat(target uuid) RETURNS jsonb
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
 SELECT CASE WHEN a.id IS NULL OR NOT a.is_active OR a.role NOT IN ('member','president','secretary','admin')
   THEN jsonb_build_object('seated',false,'voting',false)
   ELSE coalesce(
     (SELECT jsonb_build_object('seated',c.seated,'voting',c.voting) FROM public.tribunal_councilseatchange c
       WHERE c.account_id=a.id ORDER BY c.created_at DESC, c.id DESC LIMIT 1),
     jsonb_build_object('seated',a.role IN ('member','president'),'voting',a.role IN ('member','president')))
   END
 FROM (SELECT 1) one LEFT JOIN public.tribunal_account a ON a.id=target
$$;

CREATE FUNCTION public.ctm_voting_seat(target uuid) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
 SELECT coalesce((public.ctm_council_seat(target)->>'voting')::boolean,false)
$$;

-- Staff read every seat change; applicants and the worker get nothing.
CREATE FUNCTION public.ctm_council_seat_readable() RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
 SELECT NOT public.ctm_worker_caller() AND coalesce(public.ctm_actor_role() IN ('member','president','secretary','admin'),false)
$$;

-- Admin, secretary or president add a change, as themselves, for a staff account.
CREATE FUNCTION public.ctm_council_seat_writable(data jsonb) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
 SELECT NOT public.ctm_worker_caller()
   AND coalesce(public.ctm_actor_role() IN ('admin','secretary','president'),false)
   AND data->>'actor_id'=public.ctm_actor_id()::text
   AND EXISTS(SELECT 1 FROM public.tribunal_account a WHERE a.id::text=data->>'account_id'
     AND a.role IN ('member','president','secretary','admin'))
$$;

-- The change time is the database clock, so "the latest counts" cannot be forged.
CREATE FUNCTION public.ctm_council_seat_stamp() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public AS $$
BEGIN
 IF NOT public.ctm_migration_caller() THEN NEW.created_at=clock_timestamp(); END IF;
 RETURN NEW;
END $$;
