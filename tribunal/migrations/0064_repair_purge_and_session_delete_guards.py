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


# 0057 made ctm_reject_history_update RETURN OLD for the migration owner and for an
# active purge. On its BEFORE UPDATE triggers that silently discarded overwrites
# instead of refusing them. Updates are refused for every caller again (as in
# 0002); only deletes keep the 0057 purge/migration path. SECURITY DEFINER so the
# runtime roles need no EXECUTE on the private helpers it consults.
REJECT_HISTORY_UPDATE = r'''
CREATE OR REPLACE FUNCTION public.ctm_reject_history_update() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public AS $$
BEGIN
  IF TG_OP='DELETE' AND (public.ctm_migration_caller() OR public.ctm_admin_case_purge_active()) THEN RETURN OLD; END IF;
  RAISE EXCEPTION 'CTM historical records cannot be overwritten' USING ERRCODE='23514';
END $$;
REVOKE ALL ON FUNCTION public.ctm_reject_history_update() FROM PUBLIC;
'''
REJECT_HISTORY_UPDATE_0057 = r'''
CREATE OR REPLACE FUNCTION public.ctm_reject_history_update() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF public.ctm_migration_caller() OR public.ctm_admin_case_purge_active() THEN RETURN OLD; END IF;
  RAISE EXCEPTION 'CTM historical records cannot be overwritten' USING ERRCODE='23514';
END $$;
'''


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
    schema_editor.execute(REJECT_HISTORY_UPDATE)


def uninstall(apps, schema_editor):
    # Function bodies return to their 0055/0057 versions. Privileges stay revoked:
    # re-opening PUBLIC execute would restore the defect, and reversing 0055/0057
    # drops those helpers anyway.
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute(REJECT_HISTORY_UPDATE_0057)


class Migration(migrations.Migration):
    dependencies = [("tribunal", "0063_update_demo_boules_login_email")]
    operations = [migrations.RunPython(install, uninstall)]
