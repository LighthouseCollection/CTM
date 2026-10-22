"""Bind newly filed case identity to the eligible immutable answer revision."""
from django.db import migrations

INSTALL = """
CREATE FUNCTION public.ctm_filing_case_snapshot_guard() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public AS $$
DECLARE answers jsonb; own_dob date; spouse_dob date; low_dob date; high_dob date;
BEGIN
 IF public.ctm_migration_caller() OR NEW.origin<>'new' THEN RETURN NEW; END IF;
 SELECT r.answers INTO answers FROM public.tribunal_application a
 JOIN public.tribunal_answerrevision r ON r.application_id=a.id AND r.number=a.current_version
 WHERE a.id=public.ctm_filing_application() AND a.submitted_at IS NULL;
 IF answers IS NULL THEN RAISE EXCEPTION 'New case requires an eligible filing snapshot' USING ERRCODE='42501'; END IF;
 own_dob=(answers->>'birth_date')::date;
 spouse_dob=nullif(answers->>'spouse_birth_date','')::date;
 IF spouse_dob IS NOT NULL THEN low_dob=least(own_dob,spouse_dob); high_dob=greatest(own_dob,spouse_dob); END IF;
 IF NEW.marriage_date IS DISTINCT FROM (answers->>'marriage_date')::date
   OR NEW.spouse_dob_low IS DISTINCT FROM low_dob OR NEW.spouse_dob_high IS DISTINCT FROM high_dob THEN
  RAISE EXCEPTION 'Case identity must match the bound filing snapshot' USING ERRCODE='42501';
 END IF;
 RETURN NEW;
END $$;
REVOKE ALL ON FUNCTION public.ctm_filing_case_snapshot_guard() FROM PUBLIC;
CREATE TRIGGER filing_snapshot_guard BEFORE INSERT ON public.tribunal_case
 FOR EACH ROW EXECUTE FUNCTION public.ctm_filing_case_snapshot_guard();
"""
UNINSTALL = """
DROP TRIGGER filing_snapshot_guard ON public.tribunal_case;
DROP FUNCTION public.ctm_filing_case_snapshot_guard();
"""


def install(apps, schema_editor):
    if schema_editor.connection.vendor == 'postgresql':
        schema_editor.execute(INSTALL)


def uninstall(apps, schema_editor):
    if schema_editor.connection.vendor == 'postgresql':
        schema_editor.execute(UNINSTALL)


class Migration(migrations.Migration):
    dependencies = [('tribunal', '0038_runtime_grants')]
    operations = [migrations.RunPython(install, uninstall)]
