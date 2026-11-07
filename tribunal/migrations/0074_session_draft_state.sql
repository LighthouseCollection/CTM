-- #224 / D-0052: a council session moves between Draft and In progress
-- (planned) any time before it is adjourned, by admin, president or secretary.
-- ctm_council_writable (0012) only ever accepted 'planned' or 'closed', so the
-- service's back-to-draft and create-as-draft paths failed under the app role.
-- These policies are permissive, so they add exactly this case; closing keeps
-- its old rule (admin and secretary only), and the 0012 trigger still refuses
-- any change to a closed session and any date change.
CREATE FUNCTION public.ctm_session_draft_state_writable(data jsonb) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
 SELECT public.ctm_is_council()
   AND coalesce(public.ctm_actor_role() IN ('admin','president','secretary'),false)
   AND data->>'state' IN ('draft','planned')
   AND data->>'adjourned_at' IS NULL AND data->>'closed_at' IS NULL
$$;

-- A new session may start as Draft, created by the same roles as an In progress one.
CREATE FUNCTION public.ctm_session_draft_insertable(data jsonb) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
 SELECT public.ctm_is_council()
   AND coalesce(public.ctm_actor_role() IN ('admin','secretary'),false)
   AND data->>'state'='draft' AND data->>'adjourned_at' IS NULL AND data->>'closed_at' IS NULL
$$;
