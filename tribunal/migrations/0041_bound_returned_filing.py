from pathlib import Path
from django.db import migrations


def install(apps, schema_editor):
    if schema_editor.connection.vendor == "postgresql":
        schema_editor.execute(Path(__file__).with_suffix(".sql").read_text())


def uninstall(apps, schema_editor):
    if schema_editor.connection.vendor == "postgresql":
        source = Path(__file__).with_name("0037_core_policies.sql").read_text()
        original = source[source.index("CREATE FUNCTION public.ctm_filing_case"):source.index("CREATE FUNCTION public.ctm_close_allowed")]
        schema_editor.execute(original.replace("CREATE FUNCTION", "CREATE OR REPLACE FUNCTION", 1))


class Migration(migrations.Migration):
    dependencies = [("tribunal", "0040_account_administration")]
    operations = [migrations.RunPython(install, uninstall)]
