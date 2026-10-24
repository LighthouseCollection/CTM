from pathlib import Path
from django.db import migrations


def install(apps, schema_editor):
    if schema_editor.connection.vendor == "postgresql":
        schema_editor.execute(Path(__file__).with_suffix(".sql").read_text())


def uninstall(apps, schema_editor):
    if schema_editor.connection.vendor == "postgresql":
        schema_editor.execute(Path(__file__).with_name("0041_bound_returned_filing.sql").read_text())


class Migration(migrations.Migration):
    dependencies = [("tribunal", "0044_document_category_labels")]
    operations = [migrations.RunPython(install, uninstall)]
