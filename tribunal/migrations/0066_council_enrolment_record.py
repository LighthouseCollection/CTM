"""Enrolment record for the first Microsoft binding (D-0021, #65, #66).

The binding no longer trusts audit history as proof that an admin added the
member: an AFTER INSERT trigger records the enrolment itself, the binding
consumes it, and every refusal is one uniform denial.
"""
import re
from pathlib import Path
from django.db import migrations

ROOT = Path(__file__).parent


def install(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute((ROOT / "0066_council_enrolment_record.sql").read_text())


def uninstall(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    source = (ROOT / "0065_microsoft_first_binding.sql").read_text()
    binding = re.search(r"CREATE FUNCTION public.ctm_bind_microsoft_subject\(target uuid\).*?\nEND \$\$;", source, re.S).group()
    schema_editor.execute(binding.replace("CREATE FUNCTION", "CREATE OR REPLACE FUNCTION", 1))
    schema_editor.execute("DROP TRIGGER ctm_council_enrolment_record ON public.tribunal_account")
    schema_editor.execute("DROP FUNCTION public.ctm_record_council_enrolment()")
    schema_editor.execute("DROP TABLE public.ctm_council_enrolment")


class Migration(migrations.Migration):
    dependencies = [("tribunal", "0065_microsoft_first_binding")]
    operations = [migrations.RunPython(install, uninstall)]
