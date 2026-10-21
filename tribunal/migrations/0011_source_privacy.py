from pathlib import Path
from django.db import migrations

MODELS = [
    "Application",
    "AnswerRevision",
    "Submission",
    "Attachment",
    "FileVersion",
    "FileTechnicalEvent",
    "DocumentText",
    "ReportRevision",
    "MedicalRelease",
    "Message",
    "MessageRecipient",
    "Notification",
    "AuditEvent",
    "HistoricalWorkspace",
]
FUNCTIONS = [
    "ctm_anonymous_source_writable(text,jsonb)",
    "ctm_external_context_valid(boolean)",
    "ctm_paid_filing_actor(uuid)",
    "ctm_source_mutable(text,jsonb)",
    "ctm_source_deletable(text,jsonb)",
    "ctm_file_row_readable(uuid,uuid,integer)",
    "ctm_source_writable(text,jsonb)",
    "ctm_source_readable(text,jsonb)",
    "ctm_message_visible(uuid)",
    "ctm_report_visible(uuid)",
    "ctm_file_visible(uuid)",
    "ctm_attachment_visible(uuid)",
    "ctm_decree_released(uuid)",
    "ctm_application_visible(uuid)",
    "ctm_is_council()",
    "ctm_actor_role()",
    "ctm_actor_id()",
    "ctm_attachment_writable(jsonb)",
    "ctm_case_writer(uuid)",
]


def install(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute(
        Path(__file__).with_suffix(".sql").read_text(encoding="utf-8")
    )
    quote = schema_editor.quote_name
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("SELECT current_user")
        owner = cursor.fetchone()[0]
        cursor.execute(
            "SELECT rolname FROM pg_roles WHERE rolname IN ('ctm_app','ctm_worker')"
        )
        runtime_roles = [row[0] for row in cursor.fetchall()]
    entrypoints = [
        "ctm_source_readable(text,jsonb)",
        "ctm_source_writable(text,jsonb)",
        "ctm_source_mutable(text,jsonb)",
        "ctm_source_deletable(text,jsonb)",
        "ctm_paid_filing_actor(uuid)",
    ]
    for signature in FUNCTIONS + ["ctm_preserve_source_provenance()"]:
        schema_editor.execute(f"REVOKE ALL ON FUNCTION public.{signature} FROM PUBLIC")
    for role in runtime_roles:
        for signature in entrypoints:
            schema_editor.execute(
                f"GRANT EXECUTE ON FUNCTION public.{signature} TO {quote(role)}"
            )
    for name in MODELS:
        model = apps.get_model("tribunal", name)
        table = quote(model._meta.db_table)
        resource = name.lower()
        schema_editor.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        schema_editor.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        # A separate migration credential is intentionally privileged; runtime must not inherit it.
        schema_editor.execute(
            f"CREATE POLICY migration_owner ON {table} TO {quote(owner)} USING (true) WITH CHECK (true)"
        )
        schema_editor.execute(
            f"CREATE POLICY source_select ON {table} FOR SELECT USING (public.ctm_source_readable('{resource}',to_jsonb({table})))"
        )
        schema_editor.execute(
            f"CREATE POLICY source_insert ON {table} FOR INSERT WITH CHECK (public.ctm_source_writable('{resource}',to_jsonb({table})))"
        )
        schema_editor.execute(
            f"CREATE POLICY source_update ON {table} FOR UPDATE USING (public.ctm_source_readable('{resource}',to_jsonb({table})) AND public.ctm_source_mutable('{resource}',to_jsonb({table}))) WITH CHECK (public.ctm_source_writable('{resource}',to_jsonb({table})))"
        )
        schema_editor.execute(
            f"CREATE POLICY source_delete ON {table} FOR DELETE USING (public.ctm_source_deletable('{resource}',to_jsonb({table})))"
        )


def uninstall(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    for table in ["tribunal_application", "tribunal_attachment"]:
        schema_editor.execute(
            f"DROP TRIGGER IF EXISTS preserve_source_provenance ON public.{table}"
        )
    schema_editor.execute(
        "DROP FUNCTION IF EXISTS public.ctm_preserve_source_provenance()"
    )
    for name in MODELS:
        table = schema_editor.quote_name(
            apps.get_model("tribunal", name)._meta.db_table
        )
        for policy in [
            "migration_owner",
            "source_select",
            "source_insert",
            "source_update",
            "source_delete",
        ]:
            schema_editor.execute(f"DROP POLICY IF EXISTS {policy} ON {table}")
        schema_editor.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
        schema_editor.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
    for signature in FUNCTIONS:
        schema_editor.execute(f"DROP FUNCTION IF EXISTS public.{signature}")


class Migration(migrations.Migration):
    dependencies = [("tribunal", "0010_alter_recording_file_and_more")]
    operations = [migrations.RunPython(install, uninstall)]
