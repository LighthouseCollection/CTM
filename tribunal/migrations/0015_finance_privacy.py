from pathlib import Path
from django.db import migrations

MODELS = ["FeeObligation", "CheckoutIntent", "PaymentEvent", "CompletenessReview"]
ENTRYPOINTS = ["ctm_finance_readable(text,jsonb)", "ctm_review_readable(jsonb)",
               "ctm_finance_writable(text,jsonb)", "ctm_finance_notice(text,jsonb)", "ctm_fee_can_waive(uuid)"]
FUNCTIONS = ENTRYPOINTS + ["ctm_payment_scope(uuid)", "ctm_preserve_finance_context()"]


def install(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute(Path(__file__).with_suffix(".sql").read_text())
    quote = schema_editor.quote_name
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("SELECT current_user")
        owner = cursor.fetchone()[0]
        cursor.execute("SELECT rolname FROM pg_roles WHERE rolname IN ('ctm_app','ctm_worker')")
        roles = [row[0] for row in cursor.fetchall()]
    for signature in FUNCTIONS:
        schema_editor.execute(f"REVOKE ALL ON FUNCTION public.{signature} FROM PUBLIC")
    for role in roles:
        for signature in ENTRYPOINTS:
            schema_editor.execute(f"GRANT EXECUTE ON FUNCTION public.{signature} TO {quote(role)}")
    for name in MODELS:
        table = quote(apps.get_model("tribunal", name)._meta.db_table)
        resource = name.lower()
        readable = f"public.ctm_review_readable(to_jsonb({table}))" if name == "CompletenessReview" else f"public.ctm_finance_readable('{resource}',to_jsonb({table}))"
        schema_editor.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        schema_editor.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        schema_editor.execute(f"CREATE POLICY migration_owner ON {table} TO {quote(owner)} USING (true) WITH CHECK (true)")
        schema_editor.execute(f"CREATE POLICY finance_select ON {table} FOR SELECT USING ({readable})")
        schema_editor.execute(f"CREATE POLICY finance_insert ON {table} FOR INSERT WITH CHECK (public.ctm_finance_writable('{resource}',to_jsonb({table})))")
        if name in {"FeeObligation", "CheckoutIntent"}:
            schema_editor.execute(f"CREATE POLICY finance_update ON {table} FOR UPDATE USING ({readable}) WITH CHECK (public.ctm_finance_writable('{resource}',to_jsonb({table})))")
    for model in ["Notification", "AuditEvent"]:
        table = quote(apps.get_model("tribunal", model)._meta.db_table)
        schema_editor.execute(f"CREATE POLICY finance_notice ON {table} FOR INSERT WITH CHECK (public.ctm_finance_notice('{model.lower()}',to_jsonb({table})))")


def uninstall(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    for model in ["Notification", "AuditEvent"]:
        table = schema_editor.quote_name(apps.get_model("tribunal", model)._meta.db_table)
        schema_editor.execute(f"DROP POLICY IF EXISTS finance_notice ON {table}")
    for name in MODELS:
        table = schema_editor.quote_name(apps.get_model("tribunal", name)._meta.db_table)
        if name in {"FeeObligation", "CheckoutIntent"}:
            schema_editor.execute(f"DROP TRIGGER IF EXISTS preserve_finance_context ON {table}")
        for policy in ["migration_owner", "finance_select", "finance_insert", "finance_update"]:
            schema_editor.execute(f"DROP POLICY IF EXISTS {policy} ON {table}")
        schema_editor.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
        schema_editor.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
    for signature in FUNCTIONS:
        schema_editor.execute(f"DROP FUNCTION IF EXISTS public.{signature}")


class Migration(migrations.Migration):
    dependencies = [("tribunal", "0014_payment_provider_identity")]
    operations = [migrations.RunPython(install, uninstall)]
