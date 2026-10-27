"""Repair privileges and guards introduced by 0055 (draft session delete) and 0057 (admin case purge).

Forward only; earlier migrations are not rewritten. No role is created and no credential changes.
"""
from django.db import migrations

# Security-definer helpers from 0055/0057 were left executable by PUBLIC.
DEFINER_HELPERS = [
    "ctm_admin_case_purge_allowed(uuid)",
    "ctm_admin_case_purge_active()",
    "ctm_draft_session_delete_allowed(uuid)",
    "ctm_guard_draft_session_delete()",
]
# Row-policy entrypoints evaluated as the runtime app role (DELETE policies on
# tribunal_councilsession, tribunal_case, tribunal_party, tribunal_proceeding).
APP_POLICY_ENTRYPOINTS = [
    "ctm_admin_case_purge_allowed(uuid)",
    "ctm_draft_session_delete_allowed(uuid)",
]


def grant_runtime(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("SELECT 1 FROM pg_roles WHERE rolname='ctm_app'")
        if cursor.fetchone():
            for signature in APP_POLICY_ENTRYPOINTS:
                cursor.execute(f"GRANT EXECUTE ON FUNCTION public.{signature} TO ctm_app")


def install(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    for signature in DEFINER_HELPERS:
        schema_editor.execute(f"REVOKE ALL ON FUNCTION public.{signature} FROM PUBLIC")
    grant_runtime(apps, schema_editor)


def uninstall(apps, schema_editor):
    # Privileges stay revoked on reverse: re-opening PUBLIC execute would restore
    # the defect. Reversing 0055/0057 drops these functions anyway.
    return


class Migration(migrations.Migration):
    dependencies = [("tribunal", "0063_update_demo_boules_login_email")]
    operations = [migrations.RunPython(install, uninstall)]
