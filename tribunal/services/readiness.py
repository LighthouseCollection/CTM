"""Read-only deployment gate. Configuration presence is never provider acceptance."""

from django.apps import apps
from django.db import connection


def database_readiness():
    report = {"ready_for_deployment": False, "blockers": [], "checks": {}}
    if connection.vendor != "postgresql":
        report["blockers"].append("PostgreSQL is required to verify runtime ownership and RLS.")
        return report
    tables = sorted(model._meta.db_table for model in apps.get_app_config("tribunal").get_models())
    with connection.cursor() as cursor:
        cursor.execute("SELECT current_user,rolsuper,rolbypassrls,rolcreaterole,rolcreatedb,rolreplication,rolinherit FROM pg_roles WHERE rolname=current_user")
        row = cursor.fetchone()
        report["role"] = row[0]
        attributes = dict(zip(["superuser", "bypass_rls", "create_role", "create_database", "replication", "inherit"], row[1:]))
        cursor.execute("SELECT c.relname,c.relrowsecurity,c.relforcerowsecurity,r.rolname,pg_has_role(current_user,r.oid,'MEMBER'),has_table_privilege(current_user,c.oid,'SELECT') FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace JOIN pg_roles r ON r.oid=c.relowner WHERE n.nspname='public' AND c.relname=ANY(%s) ORDER BY c.relname", [tables])
        rows = cursor.fetchall()
        cursor.execute("SELECT has_schema_privilege(current_user,'public','CREATE')")
        can_create = cursor.fetchone()[0]
        cursor.execute("""SELECT p.proname FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace,
            LATERAL aclexplode(coalesce(p.proacl,acldefault('f',p.proowner))) permissions
            WHERE n.nspname='public' AND p.proname LIKE 'ctm_%%' AND p.prosecdef
              AND permissions.grantee=0 AND permissions.privilege_type='EXECUTE'""")
        public_helpers = [row[0] for row in cursor.fetchall()]
    protected = [row[0] for row in rows if row[1] and row[2]]
    unreviewed = [row[0] for row in rows if row[0] not in protected]
    owns_or_inherits = [row[0] for row in rows if row[3] == report["role"] or row[4]]
    missing_read = [row[0] for row in rows if not row[5]]
    report["checks"] = {"role_attributes": attributes, "can_create_in_public": can_create,
        "domain_model_count": len(tables), "installed_domain_table_count": len(rows),
        "forced_rls_table_count": len(protected), "unreviewed_domain_tables": unreviewed,
        "owned_or_owner_role_accessible_tables": owns_or_inherits,
        "tables_without_select_grant": missing_read, "public_security_definer_helpers": public_helpers}
    if any(attributes.values()) or can_create:
        report["blockers"].append("Runtime role has privileged role attributes or public schema CREATE access.")
    if owns_or_inherits:
        report["blockers"].append("Runtime can own or assume ownership of application tables.")
    if len(rows) != len(tables):
        report["blockers"].append("Application migrations are not fully installed.")
    if unreviewed:
        report["blockers"].append("Some domain tables still lack reviewed forced RLS or an explicit safe alternative.")
    if missing_read:
        report["blockers"].append("Runtime grant plan is incomplete; this command does not add grants.")
    if public_helpers:
        report["blockers"].append("Security-definer helpers are executable by PUBLIC.")
    report["blockers"].append("Approved 151-table reconciliation and provider/end-to-end acceptance remain incomplete.")
    return report
