"""Exercise the reviewed grants with the actual app/worker role identities."""
from contextlib import contextmanager
from importlib import import_module
import pytest
from django.apps import apps
from django.db import connection, transaction, DatabaseError
from tribunal.models import Account, Person, Case, Party, Proceeding, OpenCaseClaim, Outbox, PaymentEvent
from tribunal.services.applications import submit_application
from tribunal.db.context import database_actor

pytestmark = pytest.mark.django_db

@pytest.fixture
def granted_roles():
    if connection.vendor != 'postgresql':
        pytest.skip('PostgreSQL runtime grants')
    with connection.cursor() as cursor:
        for role in ['ctm_app','ctm_worker']:
            cursor.execute('SELECT 1 FROM pg_roles WHERE rolname=%s',[role])
            if not cursor.fetchone():
                cursor.execute(f'CREATE ROLE {role} NOLOGIN NOSUPERUSER NOBYPASSRLS NOINHERIT')
            cursor.execute(f'GRANT {role} TO CURRENT_USER')
    editor=connection.schema_editor(atomic=False)
    import_module('tribunal.migrations.0038_runtime_grants').grant_runtime(apps,editor)
    @contextmanager
    def enter(role,actor=None):
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute(f'SET LOCAL ROLE {role}')
            try:
                with database_actor(actor):
                    yield
            finally:
                if not connection.needs_rollback:
                    with connection.cursor() as cursor:
                        cursor.execute('RESET ROLE')
    return enter


def test_seven_core_tables_fail_closed_without_actor(granted_roles,people):
    for model in [Account,Person,Case,Party,Proceeding,OpenCaseClaim,Outbox]:
        with granted_roles('ctm_app'):
            assert not model.objects.exists()


def test_actual_app_grants_support_filing_and_immutable_identity(granted_roles,ready_application):
    actor=ready_application.owner
    with granted_roles('ctm_app',actor):
        submit_application(actor,ready_application.pk,'actual-app-grant',{'accepted':True,'name':'John Smith'})
    ready_application.refresh_from_db()
    with granted_roles('ctm_app',actor):
        assert Case.objects.filter(pk=ready_application.case_id).exists()
    with pytest.raises(DatabaseError):
        with granted_roles('ctm_app',actor):
            Account.objects.filter(pk=actor.pk).update(role='admin')
    with pytest.raises(DatabaseError):
        with granted_roles('ctm_app',actor):
            Person.objects.filter(pk=actor.person_id).update(first_name='Forged')


def test_worker_cannot_impersonate_council_or_create_provider_facts(granted_roles,people):
    with granted_roles('ctm_worker',people['admin']):
        assert not Account.objects.exists()
        assert not Case.objects.exists()
        with connection.cursor() as cursor:
            cursor.execute('SELECT has_table_privilege(current_user,%s,%s)',[PaymentEvent._meta.db_table,'INSERT'])
            assert cursor.fetchone()==(False,)
            cursor.execute("SELECT has_table_privilege(current_user,'django_session','SELECT')")
            assert cursor.fetchone()==(False,)
            cursor.execute("SELECT has_function_privilege(current_user,'ctm_delivery_destination(uuid)','EXECUTE')")
            assert cursor.fetchone()==(True,)


def test_actual_app_session_authentication(granted_roles,people,client):
    client.force_login(people['applicant'])
    with granted_roles('ctm_app'):
        response=client.get('/api/session/')
        assert response.status_code==200, response.content


def test_worker_retention_expires_only_eligible_private_drafts(granted_roles,unpaid_application):
    from django.utils import timezone
    from tribunal.models import Application, AnswerRevision
    from tribunal.services.retention import process_drafts
    Application.objects.filter(pk=unpaid_application.pk).update(last_activity=timezone.now()-timezone.timedelta(days=181))
    with granted_roles('ctm_worker'):
        result=process_drafts()
        assert result['expired']==1
        assert not Application.objects.filter(pk=unpaid_application.pk).exists()
    unpaid_application.refresh_from_db()
    assert unpaid_application.status=='expired'
    assert not AnswerRevision.objects.filter(application=unpaid_application).exists()
    assert Outbox.objects.filter(kind='private_orphan_cleanup').count()==4


def test_worker_dispatch_uses_restricted_destination(granted_roles,people,mailoutbox,settings):
    settings.EMAIL_HOST="synthetic-smtp.invalid"
    settings.EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend"
    from tribunal.tasks import claim_delivery, deliver
    row=Outbox.objects.create(key='role-mail',kind='submission_received',recipient=people['applicant'])
    with granted_roles('ctm_worker'):
        events=claim_delivery(row.pk)
        assert len(events)==1
        deliver(events)
    assert len(mailoutbox)==1
    assert mailoutbox[0].to==[people['applicant'].email]


def test_worker_recovers_only_verified_paid_filing(granted_roles,unpaid_application):
    from tribunal.services.payments import prepare_checkout, process_paid_checkout, finalize_paid_intent
    app=unpaid_application
    with granted_roles('ctm_app',app.owner):
        intent=prepare_checkout(app.owner,app.pk,{'accepted':True,'name':'John Smith'})
    with granted_roles('ctm_app'):
        paid=process_paid_checkout('evt_actual_worker',{'id':'cs_actual_worker','client_reference_id':str(intent.pk),
            'metadata':{'ctm_intent':str(intent.pk)},'amount_total':25000,'currency':'usd','payment_status':'paid'})
    with granted_roles('ctm_worker'):
        submission=finalize_paid_intent(paid.pk)
        assert submission.application_id==app.pk
        assert not Account.objects.exists()


def test_app_administration_and_preferences(granted_roles,people):
    from tribunal.services.identity import enroll_council, save_preferences, set_account_status
    with granted_roles('ctm_app',people['admin']):
        row=enroll_council(people['admin'],'new-member@example.test','New','Member',microsoft_subject='immutable-object')
        assert row.role=='member'
        set_account_status(people['admin'],row.pk,False)
    with granted_roles('ctm_app',people['applicant']):
        save_preferences(people['applicant'],{'ui_language':'ar','notification_language':'ar'})
    people['applicant'].refresh_from_db()
    assert people['applicant'].ui_language=='ar'


def test_provider_registration_and_lookup_under_app_role(granted_roles,rf):
    from allauth.socialaccount.models import SocialLogin, SocialAccount
    from allauth.account.models import EmailAddress
    from tribunal.auth import AccountAdapter
    request=rf.get('/accounts/google/login/callback/')
    request.session={}
    login=SocialLogin(user=Account(email='provider-new@example.test',first_name='Provider',last_name='User'),
        account=SocialAccount(provider='google',uid='verified-provider-subject'),
        email_addresses=[EmailAddress(email='provider-new@example.test',verified=True,primary=True)])
    with granted_roles('ctm_app'):
        adapter=AccountAdapter(request)
        adapter.pre_social_login(request,login)
        saved=adapter.save_user(request,login)
        assert saved.role=='applicant' and not saved.has_usable_password()
    # Simulate the provider-validated lookup callback with a fresh SocialLogin.
    second=SocialLogin(account=SocialAccount(provider='google',uid='verified-provider-subject'))
    with granted_roles('ctm_app'):
        adapter.new_user(request,second)
        second.lookup()
        assert second.user.pk==saved.pk


def test_conflicted_link_does_not_break_login_or_grant_review_authority(granted_roles,people,monkeypatch):
    from django.core.exceptions import ValidationError
    from tribunal.signals import activate_verified_case_links
    def conflict(account):
        raise ValidationError('Open case conflict')
    monkeypatch.setattr('tribunal.services.identity.activate_pending_links',conflict)
    with granted_roles('ctm_app'):
        activate_verified_case_links(sender=Account,request=None,user=people['applicant'])
