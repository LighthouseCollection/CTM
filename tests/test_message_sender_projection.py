"""An invisible Account must not erase an authorized private message page."""
import pytest
from tribunal import models as m
from tribunal.services.applications import submit_application
from tribunal.services.communications import send_message
from tribunal.services.decisions import withdraw_application
from tribunal.db.context import database_actor
from tests.test_core_policy_completion import granted_roles

pytestmark=pytest.mark.django_db


@pytest.fixture
def message_thread(ready_application,people):
    app=ready_application
    submit_application(app.owner,app.pk,'sender-projection',{'accepted':True,'name':'John Smith'})
    app.refresh_from_db()
    withdraw_application(app.owner,app.pk)
    return app


def test_private_closed_case_page_keeps_real_hidden_admin_sender(granted_roles,message_thread,people,client):
    app=message_thread
    messages=[send_message(people['admin'],app.case_id,f'Synthetic private message {n}',[app.party_id],idempotency_key=f'sender-page-{n}') for n in range(51)]
    client.force_login(app.owner)
    with granted_roles('ctm_app',session=True):
        with database_actor(app.owner):
            assert m.Message.objects.filter(case_id=app.case_id).count()==51
            assert not m.Account.objects.filter(pk=people['admin'].pk).exists()
        first=client.get(f'/api/cases/{app.case_id}/messages/?offset=0')
        assert first.status_code==200,first.content
        data=first.json()
        assert len(data['items'])==50 and data['next_offset']==50
        second=client.get(f'/api/cases/{app.case_id}/messages/?offset=50').json()
        assert len(second['items'])==1 and second['next_offset'] is None
        items=data['items']+second['items']
        assert [item['id'] for item in items]==[str(row.pk) for row in messages]
        assert all(item['sender']=='admin Test' for item in items)
        assert all(item['idempotency_key'] is None for item in items)
        assert all(item['receipts']==[{'party_id':str(app.party_id),'read_at':None}] for item in items)
        with database_actor(app.owner):
            assert not m.Account.objects.filter(pk=people['admin'].pk).exists()


def test_sender_lookup_cannot_cross_private_threads_or_enumerate_accounts(granted_roles,message_thread,people,client):
    import uuid
    from django.db import connection
    from tribunal.services.identity import link_party
    app=message_thread
    own=send_message(people['admin'],app.case_id,'Owner private',[app.party_id])
    other=m.Account.objects.create_user(email='message-other@example.test',email_verified=True)
    party=link_party(people['admin'],app.case,other)
    hidden=send_message(people['admin'],app.case_id,'OTHER PRIVATE',[party.pk])
    client.force_login(app.owner)
    with granted_roles('ctm_app',session=True):
        with database_actor(app.owner),connection.cursor() as cursor:
            cursor.execute('SELECT * FROM public.ctm_message_sender_names(%s::uuid[])',[[str(own.pk),str(hidden.pk),str(people['admin'].pk),str(uuid.uuid4())]])
            assert cursor.fetchall()==[(own.pk,'admin Test')]
            assert not m.Party.objects.filter(pk=party.pk).exists()
            assert not m.MessageRecipient.objects.filter(message=hidden).exists()
            assert not m.Account.objects.filter(pk=people['admin'].pk).exists()
        response=client.get(f'/api/cases/{app.case_id}/messages/')
        assert [item['id'] for item in response.json()['items']]==[str(own.pk)]
        assert b'OTHER PRIVATE' not in response.content
    outsider=m.Account.objects.create_user(email='message-outsider@example.test',email_verified=True)
    client.force_login(outsider)
    with granted_roles('ctm_app',session=True):
        with database_actor(outsider),connection.cursor() as cursor:
            cursor.execute('SELECT * FROM public.ctm_message_sender_names(%s::uuid[])',[[str(own.pk),str(hidden.pk)]])
            assert cursor.fetchall()==[]
        denied=client.get(f'/api/cases/{app.case_id}/messages/')
        absent=client.get(f'/api/cases/{uuid.uuid4()}/messages/')
        assert denied.status_code==absent.status_code==404 and denied.content==absent.content


@pytest.mark.parametrize('role',['admin','secretary','member','president'])
def test_council_sender_names_preserve_existing_read_authority(granted_roles,message_thread,people,client,role):
    app=message_thread
    row=send_message(people['admin'],app.case_id,'Council private',[app.party_id])
    client.force_login(people[role])
    with granted_roles('ctm_app',session=True):
        response=client.get(f'/api/cases/{app.case_id}/messages/')
        assert response.status_code==200,response.content
        assert response.json()['items'][0]['sender']=='admin Test'
        assert response.json()['items'][0]['id']==str(row.pk)


def test_no_actor_worker_and_oversized_name_lookup_denied(granted_roles,message_thread,people):
    from django.db import connection,DatabaseError
    app=message_thread
    row=send_message(people['admin'],app.case_id,'Private',[app.party_id])
    with granted_roles('ctm_app',session=True),connection.cursor() as cursor:
        cursor.execute('SELECT * FROM public.ctm_message_sender_names(%s::uuid[])',[[str(row.pk)]])
        assert cursor.fetchall()==[]
    with granted_roles('ctm_app',app.owner,session=True),connection.cursor() as cursor:
        cursor.execute('SELECT * FROM public.ctm_message_sender_names(%s::uuid[])',[[str(row.pk)]*251])
        assert cursor.fetchall()==[]
    with pytest.raises(DatabaseError,match='permission denied'):
        with granted_roles('ctm_worker'),connection.cursor() as cursor:
            cursor.execute('SELECT * FROM public.ctm_message_sender_names(%s::uuid[])',[[str(row.pk)]])


def test_inactive_sender_name_and_own_sender_key_are_retained(granted_roles,message_thread,people,client):
    app=message_thread
    row=send_message(people['admin'],app.case_id,'Original sender',[app.party_id])
    own=send_message(app.owner,app.case_id,'Own reply',[app.party_id],idempotency_key='own-private-key')
    m.Account.objects.filter(pk=people['admin'].pk).update(is_active=False)
    client.force_login(app.owner)
    with granted_roles('ctm_app',session=True):
        response=client.get(f'/api/cases/{app.case_id}/messages/')
        assert response.status_code==200,response.content
        items={item['id']:item for item in response.json()['items']}
        assert items[str(row.pk)]['sender']=='admin Test'
        assert items[str(own.pk)]['sender']=='applicant Test'
        assert items[str(own.pk)]['idempotency_key']=='own-private-key'
        assert items[str(row.pk)]['idempotency_key'] is None


def test_message_name_contract_on_each_database_adapter(message_thread,people,client):
    app=message_thread
    row=send_message(people['admin'],app.case_id,'Retained adapter message',[app.party_id])
    client.force_login(app.owner)
    response=client.get(f'/api/cases/{app.case_id}/messages/')
    assert response.status_code==200,response.content
    item=response.json()['items'][0]
    assert item['id']==str(row.pk) and item['sender']=='admin Test'
    assert item['body']=='Retained adapter message'
