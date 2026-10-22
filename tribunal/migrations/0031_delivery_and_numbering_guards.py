from pathlib import Path
from django.db import migrations

ENTRYPOINTS = ["ctm_allocate_case_number(date)", "ctm_message_delivery_valid(uuid,uuid)", "ctm_draft_warning_current(uuid,timestamptz,uuid)"]
FUNCTIONS = ENTRYPOINTS + ["ctm_guard_delivery_sources()"]


def install(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute(Path(__file__).with_suffix(".sql").read_text())
    quote = schema_editor.quote_name
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("SELECT current_user")
        owner = cursor.fetchone()[0]
        cursor.execute("SELECT rolname FROM pg_roles WHERE rolname IN ('ctm_app','ctm_worker')")
        roles = [r[0] for r in cursor.fetchall()]
    for signature in FUNCTIONS:
        schema_editor.execute(f"REVOKE ALL ON FUNCTION public.{signature} FROM PUBLIC")
    for role in roles:
        for signature in ENTRYPOINTS:
            schema_editor.execute(f"GRANT EXECUTE ON FUNCTION public.{signature} TO {quote(role)}")
    table = "tribunal_casenumbercounter"
    schema_editor.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
    schema_editor.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
    schema_editor.execute(f"CREATE POLICY migration_owner ON {table} TO {quote(owner)} USING (true) WITH CHECK (true)")
    schema_editor.execute(f"CREATE TRIGGER retained_counter_delete BEFORE DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION public.ctm_reject_history_update()")
    schema_editor.execute(f"CREATE TRIGGER counter_monotonic BEFORE UPDATE ON {table} FOR EACH ROW EXECUTE FUNCTION public.ctm_guard_delivery_sources()")
    schema_editor.execute("CREATE POLICY own_receipt_update ON tribunal_messagerecipient FOR UPDATE USING (EXISTS(SELECT 1 FROM tribunal_party p WHERE p.id=party_id AND p.account_id::text=current_setting('ctm.actor_id',true))) WITH CHECK (EXISTS(SELECT 1 FROM tribunal_party p WHERE p.id=party_id AND p.account_id::text=current_setting('ctm.actor_id',true)))")
    owner_literal = "'"+owner.replace("'", "''")+"'"
    schema_editor.execute(f"CREATE POLICY private_receipt_update ON tribunal_messagerecipient AS RESTRICTIVE FOR UPDATE USING (current_user={owner_literal} OR EXISTS(SELECT 1 FROM tribunal_party p WHERE p.id=party_id AND p.account_id::text=current_setting('ctm.actor_id',true)))")
    schema_editor.execute("CREATE TRIGGER retained_receipt_identity BEFORE UPDATE ON tribunal_messagerecipient FOR EACH ROW EXECUTE FUNCTION public.ctm_guard_delivery_sources()")
    schema_editor.execute("CREATE TRIGGER retained_outbox_result BEFORE UPDATE ON tribunal_outbox FOR EACH ROW EXECUTE FUNCTION public.ctm_guard_delivery_sources()")


def uninstall(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    for policy in ["own_receipt_update", "private_receipt_update"]:
        schema_editor.execute(f"DROP POLICY {policy} ON tribunal_messagerecipient")
    schema_editor.execute("DROP TRIGGER retained_receipt_identity ON tribunal_messagerecipient")
    schema_editor.execute("DROP TRIGGER retained_outbox_result ON tribunal_outbox")
    for trigger in ["retained_counter_delete", "counter_monotonic"]:
        schema_editor.execute(f"DROP TRIGGER {trigger} ON tribunal_casenumbercounter")
    schema_editor.execute("DROP POLICY migration_owner ON tribunal_casenumbercounter")
    schema_editor.execute("ALTER TABLE tribunal_casenumbercounter NO FORCE ROW LEVEL SECURITY")
    schema_editor.execute("ALTER TABLE tribunal_casenumbercounter DISABLE ROW LEVEL SECURITY")
    for signature in FUNCTIONS:
        schema_editor.execute(f"DROP FUNCTION public.{signature}")


class Migration(migrations.Migration):
    dependencies = [("tribunal", "0030_message_idempotency_key_outbox_lease_token_and_more")]
    operations = [migrations.RunPython(install, uninstall)]
