from django.db import migrations

IMMUTABLE_MODELS = [
    "AnswerRevision",
    "Submission",
    "PaymentEvent",
    "CompletenessReview",
    "CaseAssignment",
    "FileVersion",
    "FileTechnicalEvent",
    "AuditEvent",
    "Attendance",
    "HearingOutcome",
    "ReportQuestion",
    "TemplateVersion",
    "ReportRevision",
    "TranscriptRevision",
    "TranscriptReview",
    "MedicalRelease",
    "NoteRevision",
    "FindingRevision",
    "DecisionRevision",
    "Vote",
    "PresidentialApproval",
    "DecreeRelease",
    "AppealSupplement",
    "AppealDisposition",
    "Message",
    "AppointmentResponse",
    "SettingRevision",
    "QuestionnaireVersion",
]


def install(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute("""CREATE FUNCTION ctm_reject_history_update() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN RAISE EXCEPTION 'CTM historical records cannot be overwritten' USING ERRCODE='23514'; END $$;""")
    for name in IMMUTABLE_MODELS:
        table = apps.get_model("tribunal", name)._meta.db_table
        schema_editor.execute(
            f'CREATE TRIGGER immutable_update BEFORE UPDATE ON "{table}" FOR EACH ROW EXECUTE FUNCTION ctm_reject_history_update()'
        )


def uninstall(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    for name in IMMUTABLE_MODELS:
        table = apps.get_model("tribunal", name)._meta.db_table
        schema_editor.execute(f'DROP TRIGGER IF EXISTS immutable_update ON "{table}"')
    schema_editor.execute("DROP FUNCTION IF EXISTS ctm_reject_history_update()")


class Migration(migrations.Migration):
    dependencies = [("tribunal", "0001_initial")]
    operations = [migrations.RunPython(install, uninstall)]
