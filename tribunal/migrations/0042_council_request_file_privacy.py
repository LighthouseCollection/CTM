from pathlib import Path
import re
from django.db import migrations


def install(apps, schema_editor):
    if schema_editor.connection.vendor == "postgresql":
        schema_editor.execute(Path(__file__).with_suffix(".sql").read_text())


def uninstall(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    for filename, name in [
        ("0011_source_privacy.sql", "ctm_attachment_visible"),
        ("0017_returned_filing_privacy.sql", "ctm_file_row_readable"),
        ("0011_source_privacy.sql", "ctm_attachment_writable"),
        ("0023_request_privacy.sql", "ctm_request_source_writable"),
    ]:
        source = Path(__file__).with_name(filename).read_text()
        original = re.search(r"CREATE(?: OR REPLACE)? FUNCTION public\." + name + r"\(.*?\$\$;", source, re.S).group()
        original = original.replace("CREATE FUNCTION", "CREATE OR REPLACE FUNCTION", 1)
        # Preserve the strict JSON-boolean medical guard installed by0025.
        if name == "ctm_attachment_visible":
            original = original.replace("r.scope->>'council'='true'", "r.scope->'council'='true'::jsonb")
        schema_editor.execute(original)


class Migration(migrations.Migration):
    dependencies = [("tribunal", "0041_bound_returned_filing")]
    operations = [migrations.RunPython(install, uninstall)]
