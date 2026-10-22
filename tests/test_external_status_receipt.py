"""The exact retained bearer can learn status, never private response content."""
import uuid
import pytest
from django.utils import timezone
from tribunal import models as m
from tribunal.services.reports import send_request,complete_external,cancel_request
from tribunal.services.request_contracts import request_version
from tests.test_core_policy_completion import granted_roles
from tests.test_external_link_projection import priest_request

pytestmark=pytest.mark.django_db


def status(client,granted_roles,row,token):
    with granted_roles('ctm_app',session=True):
        return client.get(f'/external/reports/{row.pk}/status/',HTTP_AUTHORIZATION=f'Bearer {token}')


@pytest.mark.parametrize('state',['active','expired','completed','cancelled','closed','case_closed','completed_expired'])
def test_exact_holder_reads_only_status_or_minimal_receipt(granted_roles,priest_request,people,client,state):
    app,row=priest_request
    token=send_request(people['admin'],row.pk,'Private Priest','private@example.test')
    report=None
    if state.startswith('completed'):
        report=complete_external(row.pk,token,{'testimony':'PRIVATE ORIGINAL TESTIMONY'})
    elif state=='cancelled':
        row.refresh_from_db();cancel_request(people['admin'],row.pk,request_version(row))
    elif state=='closed':
        m.Proceeding.objects.filter(pk=app.proceeding_id).update(status='closed')
    elif state=='case_closed':
        m.Case.objects.filter(pk=app.case_id).update(status='closed')
    if state in {'expired','completed_expired'}:
        m.ReportRequest.objects.filter(pk=row.pk).update(expires_at=timezone.now()-timezone.timedelta(seconds=1))
    response=status(client,granted_roles,row,token)
    assert response.status_code==200,response.content
    data=response.json()
    assert set(data)=={'state','expires_at','receipt'}
    assert data['state']==({'case_closed':'closed','completed_expired':'expired'}.get(state,state))
    if state=='completed':
        assert set(data['receipt'])=={'report_id','completed_at'}
        assert data['receipt']['report_id']==str(report.pk)
        assert data['receipt']['completed_at']
    else:
        assert data['receipt'] is None
    for private in ['PRIVATE ORIGINAL TESTIMONY','Private Priest','private@example.test',token,str(app.case_id),str(app.party_id),row.title]:
        assert private not in response.content.decode()
    assert response['Cache-Control']=='private, no-store' and response['Referrer-Policy']=='no-referrer'
    # Status access never reopens a terminal or expired mutation capability.
    if state!='active':
        with granted_roles('ctm_app',session=True):
            assert client.post(f'/external/reports/{row.pk}/',{'answers':{'testimony':'overwrite'}},
                content_type='application/json',HTTP_AUTHORIZATION=f'Bearer {token}').status_code==403
    assert m.Report.objects.filter(request=row).count()==(1 if report else 0)


@pytest.mark.parametrize('bad',['missing','wrong','cross_request','reissued','query_only','cookie_only','basic'])
def test_invalid_status_capabilities_equal_nonexistent(granted_roles,priest_request,people,client,bad):
    app,row=priest_request
    token=send_request(people['admin'],row.pk,'Private Priest')
    target=row.pk
    headers={}
    suffix=''
    if bad=='wrong': token='wrong'
    if bad=='cross_request': target=uuid.uuid4()
    if bad=='reissued': send_request(people['admin'],row.pk,'Replacement Priest')
    if bad=='query_only': suffix=f'?token={token}'
    if bad=='cookie_only': client.force_login(people['admin'])
    if bad not in {'missing','query_only','cookie_only'}: headers['HTTP_AUTHORIZATION']=f'Basic {token}' if bad=='basic' else f'Bearer {token}'
    with granted_roles('ctm_app',session=True):
        response=client.get(f'/external/reports/{target}/status/{suffix}',**headers)
        absent=client.get(f'/external/reports/{uuid.uuid4()}/status/',**headers)
    assert response.status_code==absent.status_code==403
    assert response.content==absent.content==b'{"error": "link_unavailable"}'


def test_receipt_preserves_original_and_old_get_contract(granted_roles,priest_request,people,client):
    _,row=priest_request
    token=send_request(people['admin'],row.pk,'Private Priest')
    report=complete_external(row.pk,token,{'testimony':'Retained original'})
    before=list(m.ReportRevision.objects.filter(report=report).values())
    first=status(client,granted_roles,row,token)
    second=status(client,granted_roles,row,token)
    assert first.status_code==second.status_code==200
    assert first.json()==second.json()
    assert list(m.ReportRevision.objects.filter(report=report).values())==before
    with granted_roles('ctm_app',session=True):
        assert client.get(f'/external/reports/{row.pk}/',HTTP_AUTHORIZATION=f'Bearer {token}').status_code==403


def test_worker_cannot_execute_status_projection(granted_roles,priest_request):
    from django.db import connection,DatabaseError
    with pytest.raises(DatabaseError,match='permission denied'):
        with granted_roles('ctm_worker'),connection.cursor() as cursor:
            cursor.execute('SELECT public.ctm_external_status_receipt()')
    with granted_roles('ctm_app',session=True),connection.cursor() as cursor:
        cursor.execute('SELECT public.ctm_external_status_receipt()')
        assert cursor.fetchone()==(None,)


@pytest.mark.parametrize('method',['post','put','head'])
def test_status_is_read_only_for_valid_holder(granted_roles,priest_request,people,client,method):
    _,row=priest_request
    token=send_request(people['admin'],row.pk,'Private Priest')
    with granted_roles('ctm_app',session=True):
        response=getattr(client,method)(f'/external/reports/{row.pk}/status/',
            HTTP_AUTHORIZATION=f'Bearer {token}')
    assert response.status_code==405
    row.refresh_from_db()
    assert row.state=='sent' and row.saved_response=={}
    assert not m.Report.objects.filter(request=row).exists()


def test_endpoint_lifecycle_contract_on_each_database_adapter(ready_application,people,client):
    from tribunal.services.applications import submit_application
    from tribunal.services.reports import create_request
    app=ready_application
    submit_application(app.owner,app.pk,'receipt-adapter',{'accepted':True,'name':'John Smith'})
    app.refresh_from_db()
    row=create_request(people['admin'],app.proceeding_id,app.party_id,'external_priest','Private adapter request',[])
    token=send_request(people['admin'],row.pk,'Private adapter priest')
    url=f'/external/reports/{row.pk}/status/'
    def read():
        response=client.get(url,HTTP_AUTHORIZATION=f'Bearer {token}')
        assert response.status_code==200,response.content
        return response.json()
    assert read()['state']=='active' and read()['receipt'] is None
    report=complete_external(row.pk,token,{'testimony':'Private adapter original'})
    assert read()['receipt']['report_id']==str(report.pk)
    m.ReportRequest.objects.filter(pk=row.pk).update(expires_at=timezone.now()-timezone.timedelta(seconds=1))
    assert read()['state']=='expired' and read()['receipt'] is None
    assert client.get(url,HTTP_AUTHORIZATION='Bearer incorrect').status_code==403
