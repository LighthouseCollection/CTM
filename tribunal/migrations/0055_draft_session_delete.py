from django.db import migrations


FORWARD = r'''
CREATE FUNCTION public.ctm_draft_session_delete_allowed(target uuid) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
 SELECT coalesce(public.ctm_actor_role() IN ('admin','secretary'), false)
   AND target::text = current_setting('ctm.delete_draft_session', true)
   AND EXISTS (
     SELECT 1 FROM public.tribunal_councilsession session
     WHERE session.id = target AND session.state = 'draft'
   )
   AND NOT EXISTS (SELECT 1 FROM public.tribunal_agendaitem item WHERE item.session_id = target)
   AND NOT EXISTS (SELECT 1 FROM public.tribunal_attendance attendance WHERE attendance.session_id = target)
   AND NOT EXISTS (SELECT 1 FROM public.tribunal_message message WHERE message.session_id = target)
   AND NOT EXISTS (SELECT 1 FROM public.agenda_transfer_events transfer WHERE transfer.to_session_id = target)
$$;

CREATE FUNCTION public.ctm_guard_draft_session_delete() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public AS $$
BEGIN
  IF NOT public.ctm_draft_session_delete_allowed(OLD.id) THEN
    RAISE EXCEPTION 'Only an unassigned draft session can be deleted' USING ERRCODE='23514';
  END IF;
  RETURN OLD;
END $$;

DROP TRIGGER core_retained_delete ON public.tribunal_councilsession;
CREATE TRIGGER core_retained_delete BEFORE DELETE ON public.tribunal_councilsession
 FOR EACH ROW EXECUTE FUNCTION public.ctm_guard_draft_session_delete();
CREATE POLICY draft_session_delete ON public.tribunal_councilsession FOR DELETE
 USING (public.ctm_draft_session_delete_allowed(id));
'''

REVERSE = r'''
DROP POLICY IF EXISTS draft_session_delete ON public.tribunal_councilsession;
DROP TRIGGER IF EXISTS core_retained_delete ON public.tribunal_councilsession;
CREATE TRIGGER core_retained_delete BEFORE DELETE ON public.tribunal_councilsession
 FOR EACH ROW EXECUTE FUNCTION public.ctm_reject_history_update();
DROP FUNCTION IF EXISTS public.ctm_guard_draft_session_delete();
DROP FUNCTION IF EXISTS public.ctm_draft_session_delete_allowed(uuid);
'''


class Migration(migrations.Migration):
    dependencies = [("tribunal", "0054_fictitious_demo_case")]
    operations = [migrations.RunSQL(FORWARD, REVERSE)]
