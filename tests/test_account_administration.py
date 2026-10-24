"""Account management authority, retained status CAS and source-bound email."""
from copy import deepcopy
import pytest
from django.contrib.sessions.models import Session
from django.db import DatabaseError, transaction, connection
from django.test import Client
from tribunal.models import Account, AuditEvent, Outbox, Notification, Case
from tribunal.services.configuration import save_setting
from tribunal.services.identity import set_account_status
from tribunal.services.account_administration import status_version
from tests.test_core_policy_completion import granted_roles

pytestmark=pytest.mark.django_db


@pytest.fixture
def status_templates(people):
    templates={'templates':[{'code':kind,'subject_en':f'Synthetic {kind}',
        'subject_ar':f'اختبار {kind}','body_en':f'Synthetic status body {kind}',
        'body_ar':f'نص تجريبي {kind}'} for kind in ['account_suspended','account_reactivated']]}
    record=save_setting(people['admin'],'email_templates',templates,expected_version=0)
    return record


def test_account_projection_is_admin_only_and_omits_provider_secrets(granted_roles,people,client):
    client.force_login(people['secretary'])
    with granted_roles('ctm_app',session=True):
        page=client.get('/api/system/accounts/?role=member&active=true&limit=1').json()
        assert [row['id'] for row in page['items']]==[str(people['member'].pk)]
        detail=client.get(f"/api/system/accounts/{people['member'].pk}/").json()
        assert detail['status_version']==0 and detail['can_suspend'] is True
        assert not {'password','microsoft_subject','is_superuser','person_id','groups'} & set(detail)
        for query in ['role=unknown','active=1','role=member&role=admin']:
            assert client.get('/api/system/accounts/?'+query).status_code==422
    for role in ['applicant','member','president']:
        client.force_login(people[role])
        with granted_roles('ctm_app',session=True):
            assert client.get('/api/system/accounts/').status_code==403
            assert client.get(f"/api/system/accounts/{people['member'].pk}/").status_code==403


def test_status_cas_revokes_only_target_sessions_and_retains_actor(granted_roles,people,client):
    other=Client();other.force_login(people['member'])
    target_key=other.session.session_key
    unrelated=Client();unrelated.force_login(people['president'])
    unrelated_key=unrelated.session.session_key
    client.force_login(people['secretary'])
    url=f"/api/system/accounts/{people['member'].pk}/status/"
    with granted_roles('ctm_app',session=True):
        result=client.post(url,{'enabled':False,'expected_version':0},content_type='application/json')
        assert result.status_code==200,result.content
        assert result.json()['account']['status_version']==1
        assert result.json()['revoked_sessions']==1 and result.json()['notice_queued'] is False
        assert client.post(url,{'enabled':True,'expected_version':0},content_type='application/json').status_code==409
        replay=client.post(url,{'enabled':False,'expected_version':1},content_type='application/json').json()
        assert replay['account']['status_version']==1
        reactivated=client.post(url,{'enabled':True,'expected_version':1},content_type='application/json')
        assert reactivated.status_code==200 and reactivated.json()['account']['status_version']==2
        history=client.get(f"/api/system/accounts/{people['member'].pk}/status-history/?limit=1").json()
        assert history['items'][0]['actor_id']==str(people['secretary'].pk)
        assert history['items'][0]['action']=='account_reactivated' and history['next_offset']==1
    assert not Session.objects.filter(session_key=target_key).exists()
    assert Session.objects.filter(session_key=unrelated_key).exists()
    assert other.get('/api/session/').status_code==401
    assert status_version(people['member'].pk)==2


@pytest.mark.parametrize('payload',[
 {'enabled':'false','expected_version':0},{'enabled':False},
 {'enabled':False,'expected_version':True},
 {'enabled':False,'expected_version':0,'role':'admin'},
])
def test_status_rejects_untyped_or_privileged_body(granted_roles,people,client,payload):
    client.force_login(people['admin'])
    with granted_roles('ctm_app',session=True):
        result=client.post(f"/api/system/accounts/{people['member'].pk}/status/",payload,content_type='application/json')
        assert result.status_code==422,result.content
    people['member'].refresh_from_db()
    assert people['member'].is_active and status_version(people['member'].pk)==0


def test_self_and_last_admin_guards(granted_roles,people,client):
    for role,target in [('admin','admin'),('secretary','admin')]:
        client.force_login(people[role])
        with granted_roles('ctm_app',session=True):
            result=client.post(f"/api/system/accounts/{people[target].pk}/status/",{'enabled':False,'expected_version':0},content_type='application/json')
            assert result.status_code==422,result.content
    assert status_version(people['admin'].pk)==0


def test_applicant_status_requires_configured_notice_before_mutation(granted_roles,people,client):
    applicant_client=Client();applicant_client.force_login(people['applicant'])
    key=applicant_client.session.session_key
    client.force_login(people['admin'])
    with granted_roles('ctm_app',session=True):
        result=client.post(f"/api/system/accounts/{people['applicant'].pk}/status/",{'enabled':False,'expected_version':0},content_type='application/json')
        assert result.status_code==422 and 'template' in result.json()['messages'][0]
    people['applicant'].refresh_from_db()
    assert people['applicant'].is_active and Session.objects.filter(session_key=key).exists()
    assert status_version(people['applicant'].pk)==0 and not Outbox.objects.exists()


def test_status_notice_is_frozen_selected_language_and_deliverable_while_suspended(granted_roles,people,client,status_templates,settings,mailoutbox):
    from tribunal.tasks import claim_delivery,deliver
    settings.EMAIL_HOST='synthetic-mail.invalid'
    settings.EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend'
    Account.objects.filter(pk=people['applicant'].pk).update(notification_language='ar')
    client.force_login(people['admin'])
    with granted_roles('ctm_app',session=True):
        result=client.post(f"/api/system/accounts/{people['applicant'].pk}/status/",{'enabled':False,'expected_version':0},content_type='application/json')
        assert result.status_code==200,result.content
        assert result.json()['notice_queued'] is True
    event=Outbox.objects.get(kind='account_suspended')
    assert event.queued_by_id==people['admin'].pk and event.payload['language']=='ar'
    assert Notification.objects.filter(key=event.key,recipient=people['applicant']).exists()
    updated=deepcopy(status_templates.value)
    updated['templates'][0]['body_ar']='نص تجريبي جديد'
    save_setting(people['admin'],'email_templates',updated,expected_version=1)
    with granted_roles('ctm_worker'):
        deliver(claim_delivery(event.pk))
        assert not Account.objects.exists()
    assert len(mailoutbox)==1 and mailoutbox[0].to==[people['applicant'].email]
    assert mailoutbox[0].subject==status_templates.value['templates'][0]['subject_ar']
    assert mailoutbox[0].body==status_templates.value['templates'][0]['body_ar']


def test_reactivation_obsoletes_old_suspension_notice(granted_roles,people,status_templates,settings,mailoutbox):
    from tribunal.tasks import claim_delivery,deliver,SupersededDelivery
    settings.EMAIL_HOST='synthetic-mail.invalid'
    settings.EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend'
    set_account_status(people['admin'],people['applicant'].pk,False,expected_version=0)
    suspended=Outbox.objects.get(kind='account_suspended')
    set_account_status(people['secretary'],people['applicant'].pk,True,expected_version=1)
    current=Outbox.objects.get(kind='account_reactivated')
    with granted_roles('ctm_worker'):
        with pytest.raises(SupersededDelivery):
            deliver(claim_delivery(suspended.pk))
        deliver(claim_delivery(current.pk))
    assert len(mailoutbox)==1 and 'account_reactivated' in mailoutbox[0].subject


def test_unrelated_actor_cannot_queue_status_mail_and_private_helper_is_not_granted(granted_roles,people,status_templates):
    with pytest.raises(DatabaseError):
        with granted_roles('ctm_app',people['member']):
            Outbox.objects.create(kind='account_suspended',key='forged-status',recipient=people['applicant'],payload={})
    with granted_roles('ctm_app',people['admin']):
        with connection.cursor() as cursor:
            cursor.execute("SELECT has_function_privilege(current_user,'ctm_account_status_source(jsonb)','EXECUTE')")
            assert cursor.fetchone()==(False,)


def test_case_assignee_projection_uses_identity_with_duplicate_names(granted_roles,people,client):
    other=Account.objects.create_user(email='duplicate-name@example.test',role='member',email_verified=True,first_name=people['member'].first_name,last_name=people['member'].last_name)
    first=Case.objects.create(number='identity-one',assigned_member=people['member'])
    second=Case.objects.create(number='identity-two',assigned_member=other)
    client.force_login(people['member'])
    with granted_roles('ctm_app',session=True):
        rows={row['id']:row for row in client.get('/api/cases/').json()['items']}
        assert rows[str(first.pk)]['assigned_member']==rows[str(second.pk)]['assigned_member']
        assert rows[str(first.pk)]['assigned_member_id']==str(people['member'].pk)
        assert rows[str(second.pk)]['assigned_member_id']==str(other.pk)


def test_paged_account_directory_recovers_inactive_members(granted_roles,people,client):
    Account.objects.bulk_create([Account(email=f'page-member-{i}@example.test',role='member',password='!',is_active=i%2==0) for i in range(103)])
    client.force_login(people['admin'])
    with granted_roles('ctm_app',session=True):
        first=client.get('/api/system/accounts/?role=member').json()
        assert len(first['items'])==100 and first['next_offset']==100
        last=client.get('/api/system/accounts/?role=member&offset=100').json()
        assert len(last['items'])==4 and last['next_offset'] is None
        inactive=client.get('/api/system/accounts/?role=member&active=false').json()
        assert len(inactive['items'])==51
        assert all(row['can_reactivate'] and row['status_version']==0 for row in inactive['items'])


def test_unverified_status_recipient_is_not_reported_as_email_success(granted_roles,people,status_templates,settings,mailoutbox):
    from tribunal.tasks import claim_delivery,deliver
    settings.EMAIL_HOST='synthetic-mail.invalid'
    settings.EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend'
    Account.objects.filter(pk=people['applicant'].pk).update(email_verified=False)
    set_account_status(people['admin'],people['applicant'].pk,False,expected_version=0)
    event=Outbox.objects.get(kind='account_suspended')
    with granted_roles('ctm_worker'):
        with pytest.raises(RuntimeError,match='recipient'):
            deliver(claim_delivery(event.pk))
    assert not mailoutbox


def test_notice_proof_failure_rolls_back_status_sessions_and_audit(granted_roles,people,status_templates,monkeypatch):
    import tribunal.services.account_administration as service
    original=service.queue_status_notice
    def tampered(account,event,template):
        return original(account,event,{**template,'body':'tampered fixture body'})
    monkeypatch.setattr(service,'queue_status_notice',tampered)
    target_client=Client();target_client.force_login(people['applicant'])
    key=target_client.session.session_key
    with pytest.raises(DatabaseError):
        with granted_roles('ctm_app',people['admin']):
            set_account_status(people['admin'],people['applicant'].pk,False,expected_version=0)
    people['applicant'].refresh_from_db()
    assert people['applicant'].is_active and Session.objects.filter(session_key=key).exists()
    assert status_version(people['applicant'].pk)==0
    assert not Outbox.objects.exists() and not Notification.objects.exists()


@pytest.mark.parametrize('subject',['Synthetic\r\nBcc: extra@example.test','Synthetic\n','Synthetic\r'])
def test_status_subject_cannot_inject_email_headers(people,status_templates,subject):
    from django.core.exceptions import ValidationError
    value=deepcopy(status_templates.value)
    value['templates'][0]['subject_en']=subject
    with pytest.raises(ValidationError):
        save_setting(people['admin'],'email_templates',value,expected_version=1)
