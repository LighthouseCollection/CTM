"""Independent backend leaf; governance sequences it with B-S1's0051 before integration."""
import re
from pathlib import Path
from django.db import migrations


def install(apps, schema_editor):
    if schema_editor.connection.vendor == 'postgresql':
        schema_editor.execute(Path(__file__).with_suffix('.sql').read_text())


def uninstall(apps, schema_editor):
    if schema_editor.connection.vendor != 'postgresql':
        return
    root = Path(__file__).parent
    source = (root / '0049_external_paper_completion.sql').read_text()
    schema_editor.execute(source[source.index('CREATE OR REPLACE FUNCTION public.ctm_report_root_writable'):])
    source = Path(__file__).with_suffix('.sql').read_text()
    function = re.search(r'CREATE OR REPLACE FUNCTION public.ctm_media_writable\(.*?END \$\$;', source, re.S).group()
    branch = """  IF EXISTS(SELECT 1 FROM public.tribunal_report report WHERE report.id=(data->>'report_id')::uuid AND report.method='recording') THEN
   RETURN public.ctm_recording_capture_allowed(data,operation);
  END IF;
"""
    assert function.count(branch) == 1
    # Preserve0029's attributed transcript-correction branch on reversal too.
    schema_editor.execute(function.replace(branch, ''))
    schema_editor.execute('DROP FUNCTION public.ctm_recording_capture_allowed(jsonb,text)')
    schema_editor.execute('DROP FUNCTION public.ctm_recording_file_allowed(uuid,uuid)')


class Migration(migrations.Migration):
    dependencies = [('tribunal', '0050_member_administration')]
    operations = [migrations.RunPython(install, uninstall)]
