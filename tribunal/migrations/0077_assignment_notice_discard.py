"""Undo window for case assignments (#237, D-0056).

Inside core_operation 'assignment', an assignment recorder under an active
president may discard the parties' not-yet-due assignment notices for the
case being changed, so an accidental assignment sends the applicants nothing.
Only discarded_at changes, set to the current time. The core guard (latest
in 0065) is re-applied with this one exception; the reverse restores 0065.
"""
import re
from pathlib import Path
from django.db import migrations

ROOT = Path(__file__).parent
ANCHOR = ("AND OLD.delivered_at IS NULL AND OLD.discarded_at IS NULL AND "
          "(OLD.lease_until IS NULL OR OLD.lease_until<=statement_timestamp())) THEN\n"
          "    RAISE EXCEPTION 'Only the worker records delivery outcomes'")
PATCHED = ("AND OLD.delivered_at IS NULL AND OLD.discarded_at IS NULL AND "
           "(OLD.lease_until IS NULL OR OLD.lease_until<=statement_timestamp()))\n"
           "     AND NOT public.ctm_assignment_notice_discard(to_jsonb(OLD),to_jsonb(NEW)) THEN\n"
           "    RAISE EXCEPTION 'Only the worker records delivery outcomes'")

HELPER = r'''
CREATE FUNCTION public.ctm_assignment_notice_discard(old jsonb, new jsonb) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
 SELECT coalesce(
   current_setting('ctm.core_operation',true)='assignment'
   AND current_setting('ctm.assignment_member',true) IS NOT NULL
   AND public.ctm_assignment_recorder(public.ctm_actor_id())
   AND public.ctm_assignment_president(public.ctm_context_uuid('ctm.assignment_president'))
   AND (old->>'case_id')::uuid=public.ctm_context_uuid('ctm.core_target')
   AND old->>'kind' IN ('assignment_changed','case_unassigned')
   AND old->>'delivered_at' IS NULL AND old->>'discarded_at' IS NULL
   AND (old->>'due_at')::timestamptz>statement_timestamp()
   AND EXISTS(SELECT 1 FROM public.tribunal_party p
     WHERE p.case_id=(old->>'case_id')::uuid AND p.account_id=(old->>'recipient_id')::uuid)
   AND (new->'discarded_at') IS NOT NULL AND new->>'discarded_at' IS NOT NULL
   AND (new->>'discarded_at')::timestamptz BETWEEN statement_timestamp()-interval '5 minutes' AND clock_timestamp()+interval '5 minutes'
   AND (new-'discarded_at') IS NOT DISTINCT FROM (old-'discarded_at'),
 false)
$$;
REVOKE ALL ON FUNCTION public.ctm_assignment_notice_discard(jsonb,jsonb) FROM PUBLIC;
'''


def guard_0065():
    source = (ROOT / "0065_microsoft_first_binding.sql").read_text()
    return re.search(r"CREATE OR REPLACE FUNCTION public\.ctm_core_guard\(\).*?\nEND \$\$;", source, re.S).group()


def install(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute(HELPER)
    guard = guard_0065()
    assert guard.count(ANCHOR) == 1
    schema_editor.execute(guard.replace(ANCHOR, PATCHED, 1))


def uninstall(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute(guard_0065())
    schema_editor.execute("DROP FUNCTION public.ctm_assignment_notice_discard(jsonb,jsonb)")


class Migration(migrations.Migration):
    dependencies = [("tribunal", "0076_case_unassign")]
    operations = [migrations.RunPython(install, uninstall)]
