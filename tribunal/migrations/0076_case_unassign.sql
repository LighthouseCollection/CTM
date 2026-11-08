-- #237 / D-0056: an audited unassign, so Undo works on a first assignment.
--
-- The 0037 case rule for op 'assignment' requires the new assigned_member_id to
-- equal ctm.assignment_member, so NULL could never pass. This adds a separate
-- permissive UPDATE policy for exactly the unassign case; the core guard
-- (0037/0065) still lets an 'assignment' update change assigned_member_id only.
-- Same authority as recording an assignment: an assignment recorder under an
-- active president, for the case named by ctm.core_target, which must be open
-- and not scheduled for a hearing in a draft or planned session.
CREATE FUNCTION public.ctm_case_unassign_allowed(data jsonb, stage text) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
 SELECT coalesce(
   current_setting('ctm.core_operation',true)='assignment'
   AND current_setting('ctm.assignment_member',true)=''
   AND public.ctm_context_uuid('ctm.core_target')=(data->>'id')::uuid
   AND data->>'status'='open'
   AND public.ctm_assignment_recorder(public.ctm_actor_id())
   AND public.ctm_assignment_president(public.ctm_context_uuid('ctm.assignment_president'))
   AND CASE stage WHEN 'old' THEN data->>'assigned_member_id' IS NOT NULL
                  WHEN 'new' THEN data->>'assigned_member_id' IS NULL ELSE false END
   AND NOT EXISTS(SELECT 1 FROM public.tribunal_agendaitem a JOIN public.tribunal_councilsession s ON s.id=a.session_id
     WHERE a.case_id=(data->>'id')::uuid AND a.part=2 AND a.state IN ('scheduled','time_exhausted')
       AND s.state IN ('draft','planned')),
 false)
$$;
