from pathlib import Path
from django.db import migrations


def grant_runtime(apps, schema_editor):
    if schema_editor.connection.vendor != 'postgresql':
        return
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("SELECT 1 FROM pg_roles WHERE rolname='ctm_app'")
        if cursor.fetchone():
            cursor.execute('GRANT EXECUTE ON FUNCTION public.ctm_withdrawal_can_close(uuid), public.ctm_closed_case_cleanup(uuid) TO ctm_app')


def install(apps, schema_editor):
    if schema_editor.connection.vendor == 'postgresql':
        schema_editor.execute(Path(__file__).with_suffix('.sql').read_text())
        grant_runtime(apps, schema_editor)


def uninstall(apps, schema_editor):
    if schema_editor.connection.vendor == 'postgresql':
        schema_editor.execute('DROP FUNCTION public.ctm_withdrawal_can_close(uuid), public.ctm_closed_case_cleanup(uuid)')


class Migration(migrations.Migration):
    dependencies = [('tribunal', '0045_linked_first_filing')]
    operations = [migrations.RunPython(install, uninstall)]
