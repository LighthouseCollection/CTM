from pathlib import Path
import re
from django.db import migrations

TABLES = ['AnswerRevision', 'Attachment', 'AuditEvent', 'Notification']
FUNCTIONS = ['ctm_filing_source_formal(text,uuid)', 'ctm_correction_notice_visible(text)', 'ctm_returned_source_visible(text,jsonb)']


def install(apps, schema_editor):
    if schema_editor.connection.vendor != 'postgresql':
        return
    schema_editor.execute(Path(__file__).with_suffix('.sql').read_text())
    quote = schema_editor.quote_name
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("SELECT rolname FROM pg_roles WHERE rolname IN ('ctm_app','ctm_worker')")
        roles = [row[0] for row in cursor.fetchall()]
    for signature in FUNCTIONS:
        schema_editor.execute(f'REVOKE ALL ON FUNCTION public.{signature} FROM PUBLIC')
    for role in roles:
        schema_editor.execute(f'GRANT EXECUTE ON FUNCTION public.ctm_returned_source_visible(text,jsonb) TO {quote(role)}')
        if role == 'ctm_worker':
            schema_editor.execute(f'GRANT EXECUTE ON FUNCTION public.ctm_correction_notice_visible(text) TO {quote(role)}')
    for name in TABLES:
        table = apps.get_model('tribunal', name)._meta.db_table
        # The table owner must retain internal SECURITY DEFINER source access.
        schema_editor.execute(f"CREATE POLICY returned_privacy ON {quote(table)} AS RESTRICTIVE FOR SELECT USING (current_user=(SELECT pg_get_userbyid(relowner) FROM pg_class WHERE oid='public.{table}'::regclass) OR public.ctm_returned_source_visible('{name.lower()}',to_jsonb({quote(table)})))")


def uninstall(apps, schema_editor):
    if schema_editor.connection.vendor != 'postgresql':
        return
    for name in TABLES:
        table = schema_editor.quote_name(apps.get_model('tribunal', name)._meta.db_table)
        schema_editor.execute(f'DROP POLICY returned_privacy ON {table}')
    old = Path(__file__).with_name('0011_source_privacy.sql').read_text()
    original = re.search(r'CREATE FUNCTION public.ctm_file_row_readable.*?\n\$\$;', old, re.S).group()
    schema_editor.execute(original.replace('CREATE FUNCTION', 'CREATE OR REPLACE FUNCTION', 1))
    for signature in reversed(FUNCTIONS):
        schema_editor.execute(f'DROP FUNCTION public.{signature}')


class Migration(migrations.Migration):
    dependencies = [('tribunal', '0016_session_transfer_history')]
    operations = [migrations.RunPython(install, uninstall)]
