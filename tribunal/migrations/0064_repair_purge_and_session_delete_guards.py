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

# 0057 rewrote ctm_guard_history_delete as SECURITY INVOKER while making it call
# private definer helpers the runtime roles cannot execute, so a draft owner's
# permitted delete failed with "permission denied for function ctm_migration_caller".
# Same body, now SECURITY DEFINER with a pinned search_path and no PUBLIC execute
# (the pattern 0016 uses for ctm_guard_attendance_transfer_delete).
GUARD_HISTORY_DELETE = r'''
CREATE OR REPLACE FUNCTION public.ctm_guard_history_delete() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public AS $$
DECLARE disposable boolean=false;
BEGIN
  IF public.ctm_migration_caller() OR public.ctm_admin_case_purge_active() THEN RETURN OLD; END IF;
  CASE TG_TABLE_NAME
    WHEN 'tribunal_answerrevision' THEN
      SELECT a.submitted_at IS NULL AND a.status='draft' INTO disposable FROM tribunal_application a WHERE a.id=OLD.application_id;
    WHEN 'tribunal_fileversion' THEN
      SELECT a.submitted_at IS NULL AND a.status='draft' INTO disposable FROM tribunal_attachment f JOIN tribunal_application a ON a.id=f.application_id WHERE f.id=OLD.attachment_id;
    WHEN 'tribunal_filetechnicalevent', 'tribunal_documenttext' THEN
      SELECT a.submitted_at IS NULL AND a.status='draft' INTO disposable FROM tribunal_fileversion v JOIN tribunal_attachment f ON f.id=v.attachment_id JOIN tribunal_application a ON a.id=f.application_id WHERE v.id=OLD.file_id;
    ELSE disposable=false;
  END CASE;
  IF disposable IS NOT TRUE THEN
    RAISE EXCEPTION 'Submitted records and case history cannot be deleted' USING ERRCODE='23514';
  END IF;
  RETURN OLD;
END $$;
REVOKE ALL ON FUNCTION public.ctm_guard_history_delete() FROM PUBLIC;
'''
GUARD_HISTORY_DELETE_0057 = r'''
CREATE OR REPLACE FUNCTION public.ctm_guard_history_delete() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE disposable boolean=false;
BEGIN
  IF public.ctm_migration_caller() OR public.ctm_admin_case_purge_active() THEN RETURN OLD; END IF;
  CASE TG_TABLE_NAME
    WHEN 'tribunal_answerrevision' THEN
      SELECT a.submitted_at IS NULL AND a.status='draft' INTO disposable FROM tribunal_application a WHERE a.id=OLD.application_id;
    WHEN 'tribunal_fileversion' THEN
      SELECT a.submitted_at IS NULL AND a.status='draft' INTO disposable FROM tribunal_attachment f JOIN tribunal_application a ON a.id=f.application_id WHERE f.id=OLD.attachment_id;
    WHEN 'tribunal_filetechnicalevent', 'tribunal_documenttext' THEN
      SELECT a.submitted_at IS NULL AND a.status='draft' INTO disposable FROM tribunal_fileversion v JOIN tribunal_attachment f ON f.id=v.attachment_id JOIN tribunal_application a ON a.id=f.application_id WHERE v.id=OLD.file_id;
    ELSE disposable=false;
  END CASE;
  IF disposable IS NOT TRUE THEN
    RAISE EXCEPTION 'Submitted records and case history cannot be deleted' USING ERRCODE='23514';
  END IF;
  RETURN OLD;
END $$;
'''

# 0055 put a BEFORE DELETE trigger on tribunal_councilsession that allows only an
# unassigned draft. That also refused the planned-reschedule delete of the source
# session (transactions-and-acceptance: reschedule creates a new dated session and
# does not retain the cancelled one; SES01), which the 0016 session_transfer_delete
# policy already permits. The trigger now accepts either existing rule; neither
# rule is widened.
GUARD_DRAFT_SESSION_DELETE = r'''
CREATE OR REPLACE FUNCTION public.ctm_guard_draft_session_delete() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public AS $$
BEGIN
  IF NOT (public.ctm_draft_session_delete_allowed(OLD.id) OR public.ctm_session_transfer_context(OLD.id)) THEN
    RAISE EXCEPTION 'Only an unassigned draft session can be deleted' USING ERRCODE='23514';
  END IF;
  RETURN OLD;
END $$;
'''
GUARD_DRAFT_SESSION_DELETE_0055 = r'''
CREATE OR REPLACE FUNCTION public.ctm_guard_draft_session_delete() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public AS $$
BEGIN
  IF NOT public.ctm_draft_session_delete_allowed(OLD.id) THEN
    RAISE EXCEPTION 'Only an unassigned draft session can be deleted' USING ERRCODE='23514';
  END IF;
  RETURN OLD;
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
    schema_editor.execute(GUARD_HISTORY_DELETE)
    schema_editor.execute(GUARD_DRAFT_SESSION_DELETE)


def uninstall(apps, schema_editor):
    # Function bodies return to their 0055/0057 versions. Privileges stay revoked:
    # re-opening PUBLIC execute would restore the defect, and reversing 0055/0057
    # drops those helpers anyway.
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute(REJECT_HISTORY_UPDATE_0057)
    schema_editor.execute(GUARD_HISTORY_DELETE_0057)
    schema_editor.execute(GUARD_DRAFT_SESSION_DELETE_0055)


class Migration(migrations.Migration):
    dependencies = [("tribunal", "0063_update_demo_boules_login_email")]
    operations = [migrations.RunPython(install, uninstall)]
