from django.db import migrations

ADDITIONAL = ["DocumentText", "CallRecord", "SignatureAttestation"]


def install(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    for name in ADDITIONAL:
        table = apps.get_model("tribunal", name)._meta.db_table
        schema_editor.execute(
            f'CREATE TRIGGER immutable_update BEFORE UPDATE ON "{table}" FOR EACH ROW EXECUTE FUNCTION ctm_reject_history_update()'
        )
    schema_editor.execute("""CREATE FUNCTION ctm_require_open_proceeding() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE proceeding_id uuid; current_status text;
    BEGIN
      CASE TG_TABLE_NAME
        WHEN 'tribunal_answerrevision' THEN
          SELECT a.proceeding_id INTO proceeding_id FROM tribunal_application a WHERE a.id=NEW.application_id AND a.submitted_at IS NOT NULL;
        WHEN 'tribunal_noterevision' THEN
          SELECT n.proceeding_id INTO proceeding_id FROM tribunal_casenote n WHERE n.id=NEW.note_id;
        WHEN 'tribunal_reportrevision' THEN
          SELECT r.proceeding_id INTO proceeding_id FROM tribunal_report p JOIN tribunal_reportrequest r ON r.id=p.request_id WHERE p.id=NEW.report_id;
        WHEN 'tribunal_transcriptrevision' THEN
          SELECT r.proceeding_id INTO proceeding_id FROM tribunal_recording x JOIN tribunal_report p ON p.id=x.report_id JOIN tribunal_reportrequest r ON r.id=p.request_id WHERE x.id=NEW.recording_id;
        ELSE proceeding_id=NEW.proceeding_id;
      END CASE;
      IF proceeding_id IS NOT NULL THEN
        SELECT p.status INTO current_status FROM tribunal_proceeding p WHERE p.id=proceeding_id FOR UPDATE;
        IF current_status IS DISTINCT FROM 'open' THEN
          RAISE EXCEPTION 'Closed proceedings are read only' USING ERRCODE='23514';
        END IF;
      END IF;
      RETURN NEW;
    END $$;""")
    for name in [
        "AnswerRevision",
        "NoteRevision",
        "ReportRevision",
        "TranscriptRevision",
        "FindingRevision",
        "DecisionRevision",
    ]:
        table = apps.get_model("tribunal", name)._meta.db_table
        schema_editor.execute(
            f'CREATE TRIGGER require_open_proceeding BEFORE INSERT ON "{table}" FOR EACH ROW EXECUTE FUNCTION ctm_require_open_proceeding()'
        )


def uninstall(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    for name in [
        "AnswerRevision",
        "NoteRevision",
        "ReportRevision",
        "TranscriptRevision",
        "FindingRevision",
        "DecisionRevision",
    ]:
        table = apps.get_model("tribunal", name)._meta.db_table
        schema_editor.execute(
            f'DROP TRIGGER IF EXISTS require_open_proceeding ON "{table}"'
        )
    for name in ADDITIONAL:
        table = apps.get_model("tribunal", name)._meta.db_table
        schema_editor.execute(f'DROP TRIGGER IF EXISTS immutable_update ON "{table}"')
    schema_editor.execute("DROP FUNCTION IF EXISTS ctm_require_open_proceeding()")


class Migration(migrations.Migration):
    dependencies = [("tribunal", "0006_outbox_lease_until")]
    operations = [migrations.RunPython(install, uninstall)]
