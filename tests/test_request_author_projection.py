"""A readable request must not require broad visibility of its staff author's Account."""
import pytest
from tribunal import models as m
from tribunal.db.context import database_actor
from tribunal.services.applications import submit_application
from tribunal.services.council import assign_case
from tribunal.services.reports import create_request, send_request
from tests.test_core_policy_completion import granted_roles

pytestmark=pytest.mark.django_db


@pytest.fixture
def authored_requests(ready_application, people):
    app=ready_application
    submit_application(app.owner,app.pk,'request-author-projection',{'accepted':True,'name':'John Smith'})
    app.refresh_from_db()
    assign_case(people['admin'],app.case_id,people['member'].pk,people['president'].pk)
    requests=[]
    for author,kind in [(people['admin'],'intake'),(people['admin'],'medical'),(people['member'],'psychological')]:
        row=create_request(author,app.proceeding_id,app.party_id,kind,'Synthetic sent request',[])
        send_request(author,row.pk)
        requests.append(row)
    return app,requests


def test_subject_reads_real_admin_and_assigned_member_requests_without_account_visibility(granted_roles, authored_requests, people, client):
    app,requests=authored_requests
    client.force_login(app.owner)
    with granted_roles('ctm_app',session=True):
        with database_actor(app.owner):
            assert m.ReportRequest.objects.filter(pk__in=[row.pk for row in requests]).count()==3
            assert not m.Account.objects.filter(pk=people['admin'].pk).exists()
            assert m.Account.objects.filter(pk=people['member'].pk).exists()
        response=client.get(f'/api/cases/{app.case_id}/requests/')
        assert response.status_code==200,response.content
        result={row['id']:row for row in response.json()['items']}
        assert len(result)==3
        assert result[str(requests[0].pk)]['author']=='admin Test'
        assert result[str(requests[1].pk)]['author']=='admin Test'
        assert result[str(requests[2].pk)]['author']=='member Test'
        with database_actor(app.owner):
            assert not m.Account.objects.filter(pk=people['admin'].pk).exists()


@pytest.mark.parametrize('hidden_kind',['draft','external_priest','interview'])
def test_author_lookup_never_discloses_private_or_excluded_requests(granted_roles, authored_requests, people, client, hidden_kind):
    from django.db import connection
    app,_=authored_requests
    row=create_request(people['admin'],app.proceeding_id,app.party_id,'intake' if hidden_kind=='draft' else hidden_kind,'Private synthetic request',[])
    if hidden_kind!='draft':
        send_request(people['admin'],row.pk,external_name='Synthetic priest')
    client.force_login(app.owner)
    with granted_roles('ctm_app',session=True):
        with database_actor(app.owner),connection.cursor() as cursor:
            cursor.execute('SELECT * FROM public.ctm_request_author_names(%s::uuid[])',[[str(row.pk)]])
            assert cursor.fetchall()==[]
        response=client.get(f'/api/cases/{app.case_id}/requests/')
        assert response.status_code==200,response.content
        assert str(row.pk) not in [item['id'] for item in response.json()['items']]


def test_outsider_cannot_enumerate_authors_or_internal_accounts(granted_roles, authored_requests, people, client):
    import uuid
    from django.db import connection
    app,rows=authored_requests
    outsider=m.Account.objects.create_user(email='request-outsider@example.test',email_verified=True)
    client.force_login(outsider)
    with granted_roles('ctm_app',session=True):
        with database_actor(outsider),connection.cursor() as cursor:
            for targets in [[str(row.pk) for row in rows],[str(uuid.uuid4())],[str(people['admin'].pk)]]:
                cursor.execute('SELECT * FROM public.ctm_request_author_names(%s::uuid[])',[targets])
                assert cursor.fetchall()==[]
            assert not m.Account.objects.filter(pk=people['admin'].pk).exists()
            assert not m.Account.objects.filter(pk=people['member'].pk).exists()
        hidden=client.get(f'/api/cases/{app.case_id}/requests/')
        absent=client.get(f'/api/cases/{uuid.uuid4()}/requests/')
        assert hidden.status_code==absent.status_code==404
        assert hidden.content==absent.content


def test_no_actor_or_worker_cannot_use_author_lookup(granted_roles, authored_requests):
    from django.db import connection,DatabaseError
    _,rows=authored_requests
    with granted_roles('ctm_app',session=True),connection.cursor() as cursor:
        cursor.execute('SELECT * FROM public.ctm_request_author_names(%s::uuid[])',[[str(row.pk) for row in rows]])
        assert cursor.fetchall()==[]
    with pytest.raises(DatabaseError):
        with granted_roles('ctm_worker'),connection.cursor() as cursor:
            cursor.execute('SELECT * FROM public.ctm_request_author_names(%s::uuid[])',[[str(rows[0].pk)]])


@pytest.mark.parametrize('role',['member','president','secretary','admin'])
def test_council_request_author_contract_is_preserved(granted_roles, authored_requests, people, client, role):
    app,rows=authored_requests
    client.force_login(people[role])
    with granted_roles('ctm_app',session=True):
        result=client.get(f'/api/cases/{app.case_id}/requests/')
        assert result.status_code==200,result.content
        authors={item['id']:item['author'] for item in result.json()['items']}
        assert authors[str(rows[0].pk)]=='admin Test'
        assert authors[str(rows[2].pk)]=='member Test'


def test_inactive_request_author_is_not_replaced(granted_roles, authored_requests, people, client):
    app,rows=authored_requests
    m.Account.objects.filter(pk=people['admin'].pk).update(is_active=False)
    client.force_login(app.owner)
    with granted_roles('ctm_app',session=True):
        response=client.get(f'/api/cases/{app.case_id}/requests/')
        assert response.status_code==200,response.content
        assert next(item for item in response.json()['items'] if item['id']==str(rows[0].pk))['author']=='admin Test'


def test_author_projection_batches_without_silent_truncation(granted_roles, authored_requests):
    from django.db import connection
    from tribunal.services.request_projection import request_author_names
    app,rows=authored_requests
    with granted_roles('ctm_app',app.owner):
        assert request_author_names(rows*100)=={str(rows[0].pk):'admin Test',str(rows[1].pk):'admin Test',str(rows[2].pk):'member Test'}
        with connection.cursor() as cursor:
            cursor.execute('SELECT * FROM public.ctm_request_author_names(%s::uuid[])',[[str(rows[0].pk)]*251])
            assert cursor.fetchall()==[]
