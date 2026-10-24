from pathlib import Path
from django.db import migrations

MODELS = ['QuestionnaireVersion', 'ReportQuestion', 'SettingRevision']
ENTRYPOINTS = ['ctm_reference_readable(text,jsonb)', 'ctm_reference_writable(text,jsonb)']
FUNCTIONS = ENTRYPOINTS + ['ctm_configuration_safe(jsonb)']


def install(apps, schema_editor):
    if schema_editor.connection.vendor != 'postgresql':
        return
    schema_editor.execute(Path(__file__).with_suffix('.sql').read_text())
    quote = schema_editor.quote_name
    with schema_editor.connection.cursor() as cursor:
        cursor.execute('SELECT current_user')
        owner = cursor.fetchone()[0]
        cursor.execute("SELECT rolname FROM pg_roles WHERE rolname IN ('ctm_app','ctm_worker')")
        roles = [row[0] for row in cursor.fetchall()]
    for signature in FUNCTIONS:
        schema_editor.execute(f'REVOKE ALL ON FUNCTION public.{signature} FROM PUBLIC')
    for role in roles:
        for signature in ENTRYPOINTS:
            schema_editor.execute(f'GRANT EXECUTE ON FUNCTION public.{signature} TO {quote(role)}')
    for name in MODELS:
        table = quote(apps.get_model('tribunal', name)._meta.db_table)
        resource = name.lower()
        schema_editor.execute(f'ALTER TABLE {table} ENABLE ROW LEVEL SECURITY')
        schema_editor.execute(f'ALTER TABLE {table} FORCE ROW LEVEL SECURITY')
        schema_editor.execute(f'CREATE POLICY migration_owner ON {table} TO {quote(owner)} USING (true) WITH CHECK (true)')
        schema_editor.execute(f"CREATE POLICY reference_select ON {table} FOR SELECT USING (public.ctm_reference_readable('{resource}',to_jsonb({table})))")
        schema_editor.execute(f"CREATE POLICY reference_insert ON {table} FOR INSERT WITH CHECK (public.ctm_reference_writable('{resource}',to_jsonb({table})))")
        schema_editor.execute(f'CREATE TRIGGER preserve_reference_delete BEFORE DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION public.ctm_reject_history_update()')


def uninstall(apps, schema_editor):
    if schema_editor.connection.vendor != 'postgresql':
        return
    for name in MODELS:
        table = schema_editor.quote_name(apps.get_model('tribunal', name)._meta.db_table)
        schema_editor.execute(f'DROP TRIGGER preserve_reference_delete ON {table}')
        for policy in ['migration_owner', 'reference_select', 'reference_insert']:
            schema_editor.execute(f'DROP POLICY {policy} ON {table}')
        schema_editor.execute(f'ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY')
        schema_editor.execute(f'ALTER TABLE {table} DISABLE ROW LEVEL SECURITY')
    for signature in ENTRYPOINTS + ['ctm_configuration_safe(jsonb)']:
        schema_editor.execute(f'DROP FUNCTION public.{signature}')


class Migration(migrations.Migration):
    dependencies = [('tribunal', '0019_assessment_parent_guard')]
    operations = [migrations.RunPython(install, uninstall)]
