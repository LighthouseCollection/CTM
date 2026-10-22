from pathlib import Path
from django.db import migrations

MODELS = ['ReportTemplate', 'TemplateVersion']
ENTRYPOINTS = ['ctm_library_readable(text,jsonb)', 'ctm_library_writable(text,jsonb)', 'ctm_assessment_release_metadata(uuid)']
FUNCTIONS = ENTRYPOINTS + ['ctm_preserve_template_identity()']


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
        schema_editor.execute(f"CREATE POLICY library_select ON {table} FOR SELECT USING (public.ctm_library_readable('{resource}',to_jsonb({table})))")
        schema_editor.execute(f"CREATE POLICY library_insert ON {table} FOR INSERT WITH CHECK (public.ctm_library_writable('{resource}',to_jsonb({table})))")
        if name == 'ReportTemplate':
            schema_editor.execute(f"CREATE POLICY library_update ON {table} FOR UPDATE USING (public.ctm_library_writable('{resource}',to_jsonb({table}))) WITH CHECK (public.ctm_library_writable('{resource}',to_jsonb({table})))")


def uninstall(apps, schema_editor):
    if schema_editor.connection.vendor != 'postgresql':
        return
    schema_editor.execute('DROP TRIGGER preserve_template_identity ON public.tribunal_reporttemplate')
    schema_editor.execute('DROP TRIGGER preserve_template_delete ON public.tribunal_templateversion')
    for name in MODELS:
        table = schema_editor.quote_name(apps.get_model('tribunal', name)._meta.db_table)
        for policy in ['migration_owner', 'library_select', 'library_insert', 'library_update']:
            schema_editor.execute(f'DROP POLICY IF EXISTS {policy} ON {table}')
        schema_editor.execute(f'ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY')
        schema_editor.execute(f'ALTER TABLE {table} DISABLE ROW LEVEL SECURITY')
    for signature in reversed(FUNCTIONS):
        schema_editor.execute(f'DROP FUNCTION public.{signature}')


class Migration(migrations.Migration):
    dependencies = [('tribunal', '0017_returned_filing_privacy')]
    operations = [migrations.RunPython(install, uninstall)]
