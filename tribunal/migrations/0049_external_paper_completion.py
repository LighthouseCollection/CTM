from pathlib import Path
from django.db import migrations


def install(apps, schema_editor):
    if schema_editor.connection.vendor == 'postgresql':
        schema_editor.execute(Path(__file__).with_suffix('.sql').read_text())


def uninstall(apps, schema_editor):
    if schema_editor.connection.vendor == 'postgresql':
        source = Path(__file__).with_name('0023_request_privacy.sql').read_text()
        root = source[source.index('CREATE FUNCTION public.ctm_report_root_writable'):source.index('CREATE FUNCTION public.ctm_request_source_writable')]
        schema_editor.execute(root.replace('CREATE FUNCTION','CREATE OR REPLACE FUNCTION',1))
        source = Path(__file__).with_name('0042_council_request_file_privacy.sql').read_text()
        schema_editor.execute(source[source.index('CREATE OR REPLACE FUNCTION public.ctm_request_source_writable'):])
        source = Path(__file__).with_name('0047_external_status_receipt.sql').read_text()
        schema_editor.execute(source.replace('CREATE FUNCTION','CREATE OR REPLACE FUNCTION',1))
        schema_editor.execute('DROP FUNCTION public.ctm_paper_file_allowed(uuid,uuid)')


class Migration(migrations.Migration):
    dependencies = [('tribunal','0048_message_sender_projection')]
    operations = [migrations.RunPython(install,uninstall)]
