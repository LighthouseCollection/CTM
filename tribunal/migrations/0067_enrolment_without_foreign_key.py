"""Keep ctm_council_enrolment out of Django's flush path (follow-up to 0066).

A foreign key from this database-only table to tribunal_account blocked
Django's TRUNCATE of accounts. A delete trigger now removes the enrolment row.
"""
from pathlib import Path
from django.db import migrations

ROOT = Path(__file__).parent


def install(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute((ROOT / "0067_enrolment_without_foreign_key.sql").read_text())


def uninstall(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute("DROP TRIGGER ctm_council_enrolment_forget ON public.tribunal_account")
    schema_editor.execute("DROP FUNCTION public.ctm_forget_council_enrolment()")
    schema_editor.execute("DELETE FROM public.ctm_council_enrolment r WHERE NOT EXISTS("
                          "SELECT 1 FROM public.tribunal_account a WHERE a.id=r.account_id)")
    schema_editor.execute("ALTER TABLE public.ctm_council_enrolment ADD CONSTRAINT ctm_council_enrolment_account_id_fkey "
                          "FOREIGN KEY (account_id) REFERENCES public.tribunal_account(id) ON DELETE CASCADE")


class Migration(migrations.Migration):
    dependencies = [("tribunal", "0066_council_enrolment_record")]
    operations = [migrations.RunPython(install, uninstall)]
