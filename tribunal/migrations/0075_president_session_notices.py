"""The president reads and queues every council session email (#224, D-0052).

D-0052 lets the president move a session between Draft and In progress, and
going In progress announces the session (invite, update, cancel, reminder).
0070 let the president read and queue reminders only, so a president's
activation could neither find the existing rows by key nor queue new ones.
Every other condition of 0070 (recipient, session, sequence, key, no case,
manual flag) is unchanged.
"""
import re
from pathlib import Path
from django.db import migrations

SOURCE = Path(__file__).with_name("0070_session_notice_outbox.sql")
CHANGES = {
    "ctm_session_notice_allowed": (
        "OR role_name IS NULL OR NOT (role_name IN ('admin','secretary') OR (role_name='president' AND kind='session_reminder'))",
        "OR role_name IS NULL OR role_name NOT IN ('admin','secretary','president')",
    ),
    "ctm_session_reminder_readable": (
        "public.ctm_actor_role()='president' AND data->>'kind'='session_reminder'",
        "public.ctm_actor_role()='president'\n   AND data->>'kind' IN ('session_invite','session_update','session_cancel','session_reminder')",
    ),
}


def original(name):
    text = SOURCE.read_text()
    body = re.search(r"CREATE FUNCTION public\." + name + r"\(.*?\n(?:END )?\$\$;", text, re.S).group()
    return body.replace("CREATE FUNCTION", "CREATE OR REPLACE FUNCTION", 1)


def install(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    for name, (old, new) in CHANGES.items():
        sql = original(name)
        assert old in sql, name
        schema_editor.execute(sql.replace(old, new, 1))


def uninstall(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    for name in CHANGES:
        schema_editor.execute(original(name))


class Migration(migrations.Migration):
    dependencies = [("tribunal", "0074_session_draft_state")]
    operations = [migrations.RunPython(install, uninstall)]
