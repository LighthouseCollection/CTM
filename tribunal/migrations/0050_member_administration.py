"""Council display-name correction and explicit enrollment's baseline member grant."""
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
    for filename, pattern in [
        ('0037_core_policies.sql', r'CREATE FUNCTION public.ctm_core_guard\(\).*?END \$\$;'),
        ('0021_tribunal_staffmembership_staffrole.sql', r'CREATE FUNCTION public.ctm_staff_writable\(.*?\$\$;'),
    ]:
        source = (root / filename).read_text()
        function = re.search(pattern, source, re.S).group().replace('CREATE FUNCTION', 'CREATE OR REPLACE FUNCTION', 1)
        schema_editor.execute(function)


class Migration(migrations.Migration):
    dependencies = [('tribunal', '0049_external_paper_completion')]
    operations = [migrations.RunPython(install, uninstall)]
