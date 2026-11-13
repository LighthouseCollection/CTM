"""Deleting an announced Draft session can send its cancellation (#359, #116 part 1, D-0052).

A session put In progress (invites queued), answered, then returned to Draft,
could not be deleted cleanly: no cancel could be queued (0070 accepts notices
only while the session is planned) and the answers could not go with the session
(0069 refuses every delete of an answer except in a planned reschedule).

Inside the delete context that 0055 already defines (setting
ctm.delete_draft_session = the session id, admin or secretary, an unassigned
Draft with no agenda, attendance or messages, checked by
ctm_draft_session_delete_allowed(uuid)), the database now also lets the service:
  1. queue a session_cancel for that Draft session (every other 0070 condition
     stays: recipient, sequence, key, no case, admin or secretary);
  2. raise the session's ics_sequence (already allowed by 0074's Draft policy;
     0069's trigger still refuses a decrease), no change needed;
  3. delete the session's answers (3a). The answers of a Draft that is deleted
     have no history to keep: nobody was ever held to them, and the cancel
     already tells every member. Outside the context, and for a planned session,
     0069 is unchanged: answers are never changed or removed.

No new setting and no new function name: the context is 0055's. Changed:
ctm_session_notice_allowed (replaced), ctm_guard_session_response_history
(replaced), and one new policy response_draft_delete on tribunal_sessionresponse.
The reverse restores the 0075 and 0069 definitions and drops the policy.
"""
import re
from importlib import import_module
from pathlib import Path
from django.db import migrations

ROOT = Path(__file__).parent
NOTICE_OLD = "IF NOT FOUND OR session.state<>'planned' OR session.starts_at IS NULL OR session.ics_sequence<>sequence THEN"
NOTICE_NEW = (
    "IF NOT FOUND OR session.starts_at IS NULL OR session.ics_sequence<>sequence\n"
    "    OR NOT coalesce(session.state='planned'\n"
    "      OR (session.state='draft' AND kind='session_cancel' AND NOT manual\n"
    "          AND public.ctm_draft_session_delete_allowed(session.id)), false) THEN"
)
GUARD_OLD = "IF TG_OP='DELETE' AND (public.ctm_admin_case_purge_active() OR public.ctm_session_transfer_context(OLD.session_id)) THEN"
GUARD_NEW = ("IF TG_OP='DELETE' AND (public.ctm_admin_case_purge_active() OR public.ctm_session_transfer_context(OLD.session_id)\n"
             "    OR public.ctm_draft_session_delete_allowed(OLD.session_id)) THEN")


def function_source(name, sql_file):
    """CREATE OR REPLACE text of a function as an earlier migration defined it."""
    text = (ROOT / sql_file).read_text()
    body = re.search(r"CREATE FUNCTION public\." + name + r"\(.*?\n(?:END )?\$\$;", text, re.S).group()
    return body.replace("CREATE FUNCTION", "CREATE OR REPLACE FUNCTION", 1)


def current_notice_function():
    """0070's function as 0075 left it (president allowed): what the reverse restores."""
    sql = function_source("ctm_session_notice_allowed", "0070_session_notice_outbox.sql")
    old75, new75 = import_module("tribunal.migrations.0075_president_session_notices").CHANGES["ctm_session_notice_allowed"]
    return sql.replace(old75, new75, 1)


def install(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    notice = current_notice_function()
    assert NOTICE_OLD in notice
    schema_editor.execute(notice.replace(NOTICE_OLD, NOTICE_NEW, 1))
    guard = function_source("ctm_guard_session_response_history", "0069_session_response_guards.sql")
    assert GUARD_OLD in guard
    schema_editor.execute(guard.replace(GUARD_OLD, GUARD_NEW, 1))
    schema_editor.execute(
        "CREATE POLICY response_draft_delete ON public.tribunal_sessionresponse FOR DELETE "
        "USING (public.ctm_draft_session_delete_allowed(session_id))")


def uninstall(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute("DROP POLICY response_draft_delete ON public.tribunal_sessionresponse")
    schema_editor.execute(function_source("ctm_guard_session_response_history", "0069_session_response_guards.sql"))
    schema_editor.execute(current_notice_function())


class Migration(migrations.Migration):
    dependencies = [("tribunal", "0077_assignment_notice_discard")]
    operations = [migrations.RunPython(install, uninstall)]
