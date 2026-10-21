from django.db import migrations
from importlib import import_module

HISTORY = import_module(
    "tribunal.migrations.0002_immutable_history"
).IMMUTABLE_MODELS + ["DocumentText", "CallRecord", "SignatureAttestation"]


def install(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute("""CREATE FUNCTION ctm_guard_history_delete() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE disposable boolean=false;
    BEGIN
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
    END $$;""")
    for name in HISTORY + ["Case", "Party"]:
        table = apps.get_model("tribunal", name)._meta.db_table
        schema_editor.execute(
            f'CREATE TRIGGER preserve_history BEFORE DELETE ON "{table}" FOR EACH ROW EXECUTE FUNCTION ctm_guard_history_delete()'
        )


def uninstall(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    for name in HISTORY + ["Case", "Party"]:
        table = apps.get_model("tribunal", name)._meta.db_table
        schema_editor.execute(f'DROP TRIGGER IF EXISTS preserve_history ON "{table}"')
    schema_editor.execute("DROP FUNCTION IF EXISTS ctm_guard_history_delete()")


class Migration(migrations.Migration):
    dependencies = [("tribunal", "0008_account_council_microsoft_subject_unique")]
    operations = [migrations.RunPython(install, uninstall)]
