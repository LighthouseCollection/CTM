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
    import_module('tribunal.migrations.0043_request_author_projection').grant_runtime(apps,editor)
    import_module('tribunal.migrations.0044_document_category_labels').grant_runtime(apps,editor)
    import_module('tribunal.migrations.0046_withdrawal_case_scope').grant_runtime(apps,editor)
    @contextmanager
    def enter(role,actor=None,*,session=False):
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute(f'SET SESSION AUTHORIZATION {role}' if session else f'SET LOCAL ROLE {role}')
                if session:
                    cursor.execute("SET LOCAL statement_timeout='5s'")
            try:
                with database_actor(actor):
                    yield
            finally:
                if not connection.needs_rollback:
                    with connection.cursor() as cursor:
                        cursor.execute('RESET SESSION AUTHORIZATION' if session else 'RESET ROLE')
    return enter


def test_seven_core_tables_fail_closed_without_actor(granted_roles,ready_application):
    submit_application(ready_application.owner,ready_application.pk,'populated-isolation',{'accepted':True,'name':'John Smith'})
    for model in [Account,Person,Case,Party,Proceeding,OpenCaseClaim,Outbox]:
        assert model.objects.exists(), model.__name__
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


@pytest.mark.parametrize('identity', [
    {'marriage_date':'2011-05-01','spouse_dob_low':'1985-03-14','spouse_dob_high':'1987-04-02'},
    {'marriage_date':'2010-05-01','spouse_dob_low':'1980-01-01','spouse_dob_high':'1987-04-02'},
    {'marriage_date':'2010-05-01','spouse_dob_low':None,'spouse_dob_high':None},
])
def test_new_case_cannot_rebind_eligible_filing_identity(granted_roles,ready_application,identity):
    from tribunal.db.context import database_settings
    with pytest.raises(DatabaseError):
        with granted_roles('ctm_app',ready_application.owner):
            with database_settings({'ctm.core_operation':'filing','ctm.core_target':str(ready_application.pk)}):
                Case.objects.create(number='20261021-01',**identity)
    assert not Case.objects.exists()


@pytest.mark.parametrize('actor_key',['applicant','member','admin'])
def test_actual_session_user_http_identity_is_bounded(granted_roles,people,client,actor_key):
    actor=people[actor_key]
    client.force_login(actor)
    with granted_roles('ctm_app',session=True):
        with connection.cursor() as cursor:
            cursor.execute("SELECT current_user,session_user,rolsuper,rolbypassrls,rolinherit FROM pg_roles WHERE rolname=current_user")
            assert cursor.fetchone()==('ctm_app','ctm_app',False,False,False)
            cursor.execute("SELECT count(*) FROM pg_class WHERE relnamespace='public'::regnamespace AND relname LIKE 'tribunal_%' AND pg_has_role(current_user,relowner,'MEMBER')")
            assert cursor.fetchone()==(0,)
        for _ in range(3):
            response=client.get('/api/session/')
            assert response.status_code==200, response.content
            assert response.json()['id']==str(actor.pk)


def test_actual_session_user_draft_save_and_private_history(granted_roles,ready_application,people,client):
    import json, uuid
    app=ready_application
    answers={**app.revisions.get(number=app.current_version).answers,'statement':'Saved with actual session identity'}
    client.force_login(app.owner)
    with granted_roles('ctm_app',session=True):
        response=client.post(f'/api/applications/{app.pk}/',json.dumps({'answers':answers,'expected_version':app.current_version}),content_type='application/json')
        assert response.status_code==201, response.content
        history=client.get(f'/api/applications/{app.pk}/history/')
        assert history.status_code==200, history.content
        assert history.json()['items'][-1]['answers']['statement']==answers['statement']
        assert client.get('/api/system/audit/').status_code==403
    outsider=Account.objects.create_user(email='session-outsider@example.test',email_verified=True)
    for actor in [outsider,people['member'],people['admin']]:
        client.force_login(actor)
        with granted_roles('ctm_app',session=True):
            hidden=client.get(f'/api/applications/{app.pk}/history/')
            absent=client.get(f'/api/applications/{uuid.uuid4()}/history/')
            assert hidden.status_code==absent.status_code==404
            assert hidden.content==absent.content


def test_case_pagination_recovers_all_rows_with_stable_ties(granted_roles,people,client):
    from django.utils import timezone
    stamp=timezone.now()
    Case.objects.bulk_create([Case(number=f'page-{i}',created_at=stamp) for i in range(103)])
    expected=[str(row.pk) for row in Case.objects.order_by('-created_at','-id')]
    client.force_login(people['admin'])
    with granted_roles('ctm_app',session=True):
        first=client.get('/api/cases/').json()
        assert len(first['items'])==100 and first['next_offset']==100
        last=client.get('/api/cases/?offset=100').json()
        assert len(last['items'])==3 and last['next_offset'] is None
        assert [x['id'] for x in first['items']+last['items']]==expected
        assert client.get('/api/cases/?offset=103').json()['items']==[]


def test_case_page_continuation_does_not_count_foreign_cases(granted_roles,ready_application,client):
    app=ready_application
    submit_application(app.owner,app.pk,'page-own-case',{'accepted':True,'name':'John Smith'})
    app.refresh_from_db()
    Case.objects.bulk_create([Case(number=f'foreign-page-{i}') for i in range(5)])
    client.force_login(app.owner)
    with granted_roles('ctm_app',session=True):
        page=client.get('/api/cases/?limit=1').json()
        assert [x['id'] for x in page['items']]==[str(app.case_id)]
        assert page['next_offset'] is None


@pytest.mark.parametrize('query',['offset=-1','offset=1.5','offset=abc','limit=0','limit=251','offset=0&offset=1','limit=1&limit=2','offset=9223372036854775808'])
def test_pagination_rejects_invalid_parameters(granted_roles,people,client,query):
    client.force_login(people['admin'])
    with granted_roles('ctm_app',session=True):
        for url in ['/api/cases/','/api/system/audit/']:
            response=client.get(url+'?'+query)
            assert response.status_code==422, response.content


@pytest.mark.parametrize('endpoint',['case','system'])
def test_audit_pagination_recovers_beyond_old_cap(granted_roles,people,client,endpoint):
    from django.utils import timezone
    from tribunal.models import AuditEvent
    case=Case.objects.create(number='audit-pages')
    stamp=timezone.now()
    events=AuditEvent.objects.bulk_create([AuditEvent(case=case,actor=people['admin'],action='fixture_action',source='pagination.fixture',created_at=stamp) for _ in range(253)])
    expected=[str(row.pk) for row in sorted(events,key=lambda row:row.pk,reverse=True)]
    url=f'/api/cases/{case.pk}/audit/' if endpoint=='case' else '/api/system/audit/'
    client.force_login(people['admin'])
    with granted_roles('ctm_app',session=True):
        first=client.get(url).json()
        assert len(first['items'])==250 and first['next_offset']==250
        last=client.get(url+'?offset=250').json()
        assert len(last['items'])==3 and last['next_offset'] is None
        assert [x['id'] for x in first['items']+last['items']]==expected


@pytest.mark.parametrize('endpoint',['case','system'])
def test_audit_privacy_precedes_visible_offset(granted_roles,ready_application,people,client,endpoint):
    from django.utils import timezone
    from tribunal.models import AuditEvent
    from tribunal.services.applications import review_application,save_answers
    from tribunal.services.filing_privacy import audit_visible
    app=ready_application
    submission=submit_application(app.owner,app.pk,'privacy-page',{'accepted':True,'name':'John Smith'})
    review_application(people['admin'],app.pk,'reject','Please correct the statement')
    app.refresh_from_db()
    revision=save_answers(app.owner,app.pk,{**app.revisions.get(number=app.current_version).answers,'statement':'Private correction'},app.current_version)
    AuditEvent.objects.bulk_create([AuditEvent(case=app.case,actor=app.owner,action='answers_saved',source='tribunal.answerrevision',source_id=revision.pk,created_at=timezone.now()+timezone.timedelta(minutes=1)) for _ in range(10)])
    AuditEvent.objects.bulk_create([AuditEvent(case=app.case,actor=people['admin'],action='visible_fixture',source='pagination.fixture') for _ in range(3)])
    qs=AuditEvent.objects.filter(case=app.case) if endpoint=='case' else AuditEvent.objects.all()
    expected=[str(row.pk) for row in qs.order_by('-created_at','-id') if audit_visible(row)]
    assert len(expected)>2
    url=f'/api/cases/{app.case_id}/audit/' if endpoint=='case' else '/api/system/audit/'
    client.force_login(people['admin'])
    actual=[]
    with granted_roles('ctm_app',session=True):
        offset=0
        for _ in range(len(expected)+1):
            response=client.get(url+f'?limit=2&offset={offset}')
            assert response.status_code==200,response.content
            page=response.json()
            actual.extend(row['id'] for row in page['items'])
            offset=page['next_offset']
            if offset is None:break
        else:
            pytest.fail('Continuation did not terminate')
    assert actual==expected


def test_linked_first_petition_without_optional_spouse_dob(granted_roles, ready_application, people):
    from tribunal.services.identity import link_party
    from tribunal.services.applications import start_application, save_answers, waive_fee
    from tribunal.models import Attachment, FileVersion, FileTechnicalEvent, Submission
    first = ready_application
    submit_application(first.owner, first.pk, 'linked-first', {'accepted': True, 'name': 'John Smith'})
    first.refresh_from_db()
    frozen = (first.party_id, first.proceeding_id, first.case_id)
    second = Account.objects.create_user(email='linked-second@example.test', first_name='Jane',
        last_name='Smith', role='applicant', email_verified=True)
    with granted_roles('ctm_app', people['admin'], session=True):
        party = link_party(people['admin'], first.case, second)
    with granted_roles('ctm_app', second, session=True):
        app = start_application(second, first.case_id)
        answers = {
            'first_name': 'Jane', 'last_name': 'Smith', 'birth_date': '1987-04-02', 'gender': 'F',
            'marriage_date': '2010-05-01', 'grounds': ['infidelity'], 'statement': 'Statement'}
        save_answers(second, app.pk, answers, 0)
    for category in ['MC', 'CMC', 'CDD', 'PHOTO']:
        attachment = Attachment.objects.create(application=app, owner=second, category=category)
        file = FileVersion.objects.create(attachment=attachment, number=1, object_key=f'test/{attachment.pk}',
            original_name='file.pdf', display_name='file.pdf', mime_type='image/jpeg' if category=='PHOTO' else 'application/pdf',
            byte_count=5, sha256='b'*64, actor=second)
        FileTechnicalEvent.objects.create(file=file, task='scan', result='clean')
    waive_fee(people['admin'], app.pk)
    with granted_roles('ctm_app', second, session=True):
        submit_application(second, app.pk, 'linked-second', {'accepted': True, 'name': 'Jane Smith'})
    app.refresh_from_db()
    first.refresh_from_db()
    assert app.party_id == party.pk
    assert app.case_id == first.case_id and app.proceeding_id == first.proceeding_id
    assert (first.party_id, first.proceeding_id, first.case_id) == frozen
    assert Submission.objects.filter(application=app).count() == 1
    assert Submission.objects.filter(application=first).count() == 1
    assert Party.objects.filter(case=first.case).count() == 2


@pytest.mark.parametrize('missing', ['none', 'party', 'claim', 'wrong_person', 'closed_case', 'closed_proceeding', 'foreign_case', 'unpaid'])
def test_linked_filing_requires_complete_own_binding(granted_roles, ready_application, missing):
    from tribunal.models import Application, FeeObligation
    from tribunal.db.context import database_settings
    actor = ready_application.owner
    case = Case.objects.create(number='20261022-91', status='open')
    proceeding = Proceeding.objects.create(case=case, kind='original', status='open')
    person = actor.person
    if missing == 'wrong_person':
        person = Person.objects.create(first_name='Other', last_name='Person')
    if missing != 'party':
        Party.objects.create(case=case, account=actor, person=person, slot='A', name='Linked')
    if missing != 'claim':
        OpenCaseClaim.objects.create(case=case, person=actor.person)
    Application.objects.filter(pk=ready_application.pk).update(case=case)
    # Remove optional DOB so the legacy exact-marriage branch cannot authorize this.
    from tribunal.models import AnswerRevision
    revision = AnswerRevision.objects.get(application=ready_application, number=ready_application.current_version)
    revision.answers.pop('spouse_birth_date', None)
    from tribunal.services.applications import save_answers
    save_answers(actor, ready_application.pk, revision.answers, ready_application.current_version)
    if missing == 'closed_case':
        Case.objects.filter(pk=case.pk).update(status='closed')
    if missing == 'closed_proceeding':
        Proceeding.objects.filter(pk=proceeding.pk).update(status='closed')
    if missing == 'unpaid':
        FeeObligation.objects.filter(application=ready_application).update(status='unpaid')
    target = Case.objects.create(number='20261022-92', status='open').pk if missing == 'foreign_case' else case.pk
    from contextlib import nullcontext
    with nullcontext() if missing == 'none' else pytest.raises(DatabaseError, match='row-level security'):
        with granted_roles('ctm_app', actor, session=True):
            with database_settings({'ctm.core_operation': 'filing', 'ctm.core_target': str(ready_application.pk)}):
                if missing in {'party', 'foreign_case'}:
                    Party.objects.create(case_id=target, account=actor, person=actor.person, slot='A', name='Own')
                else:
                    assert Party.objects.filter(case=case, account=actor).update(case_id=target, name='Own') == 1
