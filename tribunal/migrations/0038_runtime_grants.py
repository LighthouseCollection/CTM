"""Fresh-runtime grants for existing roles only; never provisions or changes credentials."""
from pathlib import Path
from django.db import migrations

WORKER_READ = ['Outbox','Account','Person','Application','AnswerRevision','Submission','FeeObligation','CheckoutIntent',
 'PaymentEvent','Attachment','FileVersion','FileTechnicalEvent','Case','Party','Proceeding','OpenCaseClaim','QuestionnaireVersion','AuditEvent','Notification']
WORKER_INSERT = ['Submission','AuditEvent','Notification','Outbox','Case','Party','Proceeding','OpenCaseClaim']
WORKER_UPDATE = ['Outbox','Application','CheckoutIntent','Person','Party','Case','FeeObligation','Attachment']
WORKER_FUNCTIONS = ['ctm_delivery_destination(uuid)','ctm_process_retention(timestamptz)',
 'ctm_orphan_cleanup_allowed(text)','ctm_correction_notice_visible(text)','ctm_message_delivery_valid(uuid,uuid)',
 'ctm_draft_warning_current(uuid,timestamptz,uuid)','ctm_testimony_delivery_valid(uuid,integer,uuid)',
 'ctm_session_delivery_closed(uuid)','ctm_paid_filing_actor(uuid)','ctm_allocate_case_number(date)']
APP_EXTRA = ['ctm_applicant_parties(uuid)','ctm_delay_digest(uuid,timestamptz)','ctm_allocate_case_number(date)','ctm_correction_notice_visible(text)','ctm_message_delivery_valid(uuid,uuid)',
 'ctm_draft_warning_current(uuid,timestamptz,uuid)','ctm_testimony_delivery_valid(uuid,integer,uuid)',
 'ctm_session_delivery_closed(uuid)','ctm_media_status(uuid)','ctm_assessment_release_metadata(uuid)']


def grant_runtime(apps, schema_editor):
    q = schema_editor.quote_name
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("SELECT rolname,rolsuper,rolbypassrls,rolcreaterole,rolcreatedb,rolreplication,rolinherit FROM pg_roles WHERE rolname IN ('ctm_app','ctm_worker')")
        roles = cursor.fetchall()
    models = list(apps.get_app_config('tribunal').get_models())
    domain_tables = [model._meta.db_table for model in models]
    for role,*flags in roles:
        if any(flags):
            raise RuntimeError(f'{role} has privileged attributes; runtime grants refused without changing the role')
        with schema_editor.connection.cursor() as cursor:
            cursor.execute("SELECT 1 FROM pg_class WHERE relname=ANY(%s) AND pg_has_role(%s,relowner,'MEMBER') LIMIT 1", [domain_tables,role])
            if cursor.fetchone():
                raise RuntimeError(f'{role} can assume a domain owner; runtime grants refused')
        schema_editor.execute(f'GRANT USAGE ON SCHEMA public TO {q(role)}')
        for table in domain_tables:
            schema_editor.execute(f'REVOKE ALL ON TABLE {q(table)} FROM {q(role)}')
        if role=='ctm_app':
            for table in domain_tables:
                schema_editor.execute(f'GRANT SELECT,INSERT,UPDATE,DELETE ON TABLE {q(table)} TO {q(role)}')
            # Provider/session framework state is app-only; never worker authority.
            framework = ['django_session','django_content_type','auth_permission','auth_group','auth_group_permissions',
              'tribunal_account_groups','tribunal_account_user_permissions','account_emailaddress','account_emailconfirmation',
              'socialaccount_socialaccount','socialaccount_socialtoken','socialaccount_socialapp','socialaccount_socialapp_sites','django_site']
            with schema_editor.connection.cursor() as cursor:
                cursor.execute("SELECT tablename FROM pg_tables WHERE schemaname='public' AND tablename=ANY(%s)",[framework])
                installed = [row[0] for row in cursor.fetchall()]
            for table in installed:
                privileges = 'SELECT' if table in {'django_content_type','auth_permission','auth_group','auth_group_permissions','tribunal_account_groups','tribunal_account_user_permissions','socialaccount_socialapp','socialaccount_socialapp_sites','django_site'} else 'SELECT,INSERT,UPDATE,DELETE'
                schema_editor.execute(f'GRANT {privileges} ON TABLE {q(table)} TO {q(role)}')
            tables = domain_tables
            functions = APP_EXTRA
        else:
            for names,privilege in [(WORKER_READ,'SELECT'),(WORKER_INSERT,'INSERT'),(WORKER_UPDATE,'UPDATE')]:
                for name in names:
                    table=apps.get_model('tribunal',name)._meta.db_table
                    schema_editor.execute(f'GRANT {privilege} ON TABLE {q(table)} TO {q(role)}')
            tables = [apps.get_model('tribunal',name)._meta.db_table for name in WORKER_READ]
            functions = WORKER_FUNCTIONS
        # Only direct policy entrypoints for the granted tables; helpers retain
        # definer ownership and are not generally callable by the runtime role.
        with schema_editor.connection.cursor() as cursor:
            cursor.execute("""SELECT DISTINCT p.oid::regprocedure::text FROM pg_proc p JOIN pg_depend d ON d.refobjid=p.oid
              JOIN pg_policy policy ON d.objid=policy.oid JOIN pg_class t ON t.oid=policy.polrelid
              WHERE d.classid='pg_policy'::regclass AND d.refclassid='pg_proc'::regclass
                AND t.relname=ANY(%s) AND p.proname LIKE 'ctm_%%'""",[tables])
            entrypoints=[row[0] for row in cursor.fetchall()]
        for function in set(functions+entrypoints):
            schema_editor.execute(f'GRANT EXECUTE ON FUNCTION {function} TO {q(role)}')
        if role=='ctm_app':
            with schema_editor.connection.cursor() as cursor:
                cursor.execute("SELECT sequencename FROM pg_sequences WHERE schemaname='public' AND sequencename LIKE ANY(%s)",[['account_%','socialaccount_%','django_%']])
                sequences=[row[0] for row in cursor.fetchall()]
            for sequence in sequences:
                schema_editor.execute(f'GRANT USAGE,SELECT ON SEQUENCE {q(sequence)} TO {q(role)}')


def install(apps,schema_editor):
    if schema_editor.connection.vendor=='postgresql':
        schema_editor.execute(Path(__file__).with_name('0038_worker_retention.sql').read_text())
        grant_runtime(apps,schema_editor)


def uninstall(apps,schema_editor):
    if schema_editor.connection.vendor=='postgresql':
        schema_editor.execute('DROP TRIGGER worker_fee_guard ON tribunal_feeobligation')
        schema_editor.execute('DROP TRIGGER worker_finance_guard ON tribunal_checkoutintent')
        schema_editor.execute('DROP FUNCTION public.ctm_worker_finance_guard()')
        schema_editor.execute('DROP FUNCTION public.ctm_process_retention(timestamptz)')
        # Deliberately remove this reviewed grant plan on reversal. Prior grants
        # cannot be inferred; the operator must reapply an explicitly reviewed plan.
        with schema_editor.connection.cursor() as cursor:
            cursor.execute("SELECT rolname FROM pg_roles WHERE rolname IN ('ctm_app','ctm_worker')")
            roles=[row[0] for row in cursor.fetchall()]
        for role in roles:
            for model in apps.get_app_config('tribunal').get_models():
                schema_editor.execute(f'REVOKE ALL ON TABLE {schema_editor.quote_name(model._meta.db_table)} FROM {schema_editor.quote_name(role)}')


class Migration(migrations.Migration):
    dependencies=[('tribunal','0037_core_policies')]
    operations=[migrations.RunPython(install,uninstall)]
