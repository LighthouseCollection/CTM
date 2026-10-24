"""Retain a clean council paper original without granting applicant/link writes."""
import pytest
from django.utils import timezone
from tribunal import models as m
from tribunal.services.reports import send_request,complete_external_paper,revise_report
from tribunal.services.request_contracts import request_version
from tests.test_core_policy_completion import granted_roles
from tests.test_external_link_projection import priest_request

pytestmark=pytest.mark.django_db


@pytest.fixture
def paper_source(priest_request,people,settings,tmp_path):
    app,row=priest_request
    settings.MEDIA_ROOT=tmp_path
    token=send_request(people['admin'],row.pk,'Synthetic Priest')
    row.refresh_from_db()
    attachment=m.Attachment.objects.create(case=app.case,proceeding=app.proceeding,report_request=row,
        category='REPORT',owner=None,visibility='council')
    file=m.FileVersion.objects.create(attachment=attachment,number=1,object_key=f'paper/{attachment.pk}.pdf',
        original_name='paper.pdf',display_name='paper.pdf',mime_type='application/pdf',byte_count=5,sha256='e'*64,actor=people['admin'])
    m.FileTechnicalEvent.objects.create(file=file,task='scan',result='clean')
    from tribunal.services.files import private_path
    path=private_path(file.object_key);path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b'%PDF-')
    return app,row,file,token


def test_council_paper_completion_keeps_original_and_stops_link(granted_roles,paper_source,people,client):
    app,row,file,token=paper_source
    date=timezone.localdate().isoformat()
    client.force_login(people['admin'])
    payload={'file_id':str(file.pk),'completion_date':date,'expected_version':request_version(row)}
    url=f'/api/requests/{row.pk}/paper-completion/'
    with granted_roles('ctm_app',session=True):
        response=client.post(url,payload,content_type='application/json')
        assert response.status_code==201,response.content
        replay=client.post(url,payload,content_type='application/json')
        assert replay.status_code==201 and replay.json()==response.json()
        original=client.get(f'/api/files/{file.pk}/')
        assert original.status_code==200 and b''.join(original.streaming_content)==b'%PDF-'
        listed=client.get(f'/api/cases/{app.case_id}/reports/').json()['items']
        assert listed[0]['method']=='paper' and listed[0]['can_revise'] is False
        assert listed[0]['answers']=={'files':[str(file.pk)]}
        assert listed[0]['author_id']==str(people['admin'].pk)
    report=m.Report.objects.get(pk=response.json()['id'])
    assert report.author_id==people['admin'].pk and report.method=='paper'
    assert report.revisions.count()==1
    assert report.revisions.get().actor_id==people['admin'].pk
    assert m.AuditEvent.objects.filter(action='external_paper_report_submitted',source_id=report.pk,actor=people['admin']).count()==1
    assert m.Notification.objects.filter(kind='report_received',case=app.case).count()==1
    row.refresh_from_db();file.refresh_from_db()
    assert row.state=='completed' and file.sha256=='e'*64
    client.logout()
    with granted_roles('ctm_app',session=True):
        assert client.get(f'/external/reports/{row.pk}/',HTTP_AUTHORIZATION=f'Bearer {token}').status_code==403
        status=client.get(f'/external/reports/{row.pk}/status/',HTTP_AUTHORIZATION=f'Bearer {token}')
        assert status.status_code==200 and status.json()['receipt']['report_id']==str(report.pk)
    from django.core.exceptions import PermissionDenied
    with pytest.raises(PermissionDenied):
        with granted_roles('ctm_app',people['admin'],session=True):
            revise_report(people['admin'],report.pk,{'files':[]},expected_version=1)
    client.force_login(app.owner)
    with granted_roles('ctm_app',session=True):
        assert client.get(f'/api/cases/{app.case_id}/reports/').json()['items']==[]
        assert client.get(f'/api/files/{file.pk}/').status_code==404


@pytest.mark.parametrize('bad',['pending','rejected','stale','wrong_category','wrong_request','future','version','unassigned'])
def test_paper_completion_rejects_ineligible_sources_without_report(granted_roles,paper_source,people,bad):
    from django.core.exceptions import ValidationError,PermissionDenied
    app,row,file,_=paper_source
    actor=people['admin'];date=timezone.localdate().isoformat();version=request_version(row)
    if bad in {'pending','rejected'}:
        m.FileTechnicalEvent.objects.create(file=file,task='scan',result=bad)
    elif bad=='stale':
        m.FileVersion.objects.create(attachment=file.attachment,number=2,object_key=f'paper/new-{file.pk}',original_name='new.pdf',display_name='new.pdf',mime_type='application/pdf',byte_count=5,sha256='f'*64,actor=actor)
    elif bad=='wrong_category':
        attachment=m.Attachment.objects.create(case=app.case,proceeding=app.proceeding,report_request=row,category='EVD',owner=None,visibility='council')
        file=m.FileVersion.objects.create(attachment=attachment,number=1,object_key=f'paper/wrong-{attachment.pk}',original_name='wrong.pdf',display_name='wrong.pdf',mime_type='application/pdf',byte_count=5,sha256='f'*64,actor=actor)
        m.FileTechnicalEvent.objects.create(file=file,task='scan',result='clean')
    elif bad=='wrong_request':
        from tribunal.services.reports import create_request
        other=create_request(actor,app.proceeding_id,app.party_id,'external_priest','Other request',[])
        send_request(actor,other.pk,'Other priest')
        row=other;row.refresh_from_db();version=request_version(row)
    elif bad=='future':date=(timezone.localdate()+timezone.timedelta(days=1)).isoformat()
    elif bad=='version':version='stale'
    elif bad=='unassigned':actor=people['president']
    denied=(ValidationError,PermissionDenied)
    with pytest.raises(denied):
        with granted_roles('ctm_app',actor,session=True):
            complete_external_paper(actor,row.pk,file.pk,date,expected_version=version)
    assert not m.Report.objects.filter(request=row).exists()
    row.refresh_from_db();assert row.state=='sent'


@pytest.mark.parametrize('bad',['no_context','wrong_file','wrong_actor','wrong_date','revision_answers','second_revision'])
def test_raw_paper_writes_cannot_bypass_original_binding(granted_roles,paper_source,people,bad):
    from django.db import DatabaseError
    from tribunal.db.context import database_settings
    app,row,file,_=paper_source
    date=timezone.localdate()
    context={'ctm.paper_request':str(row.pk),'ctm.paper_file':str(file.pk),'ctm.paper_date':date.isoformat()}
    if bad=='no_context':context={}
    if bad=='wrong_file':context['ctm.paper_file']=str(app.pk)
    with pytest.raises(DatabaseError):
        with granted_roles('ctm_app',people['admin'],session=True),database_settings(context):
            report=m.Report.objects.create(request=row,author=people['member'] if bad=='wrong_actor' else people['admin'],
                method='paper',completion_date=date-timezone.timedelta(days=1) if bad=='wrong_date' else date)
            m.ReportRevision.objects.create(report=report,number=2 if bad=='second_revision' else 1,
                answers={'files':[]} if bad=='revision_answers' else {'files':[str(file.pk)]},observations='',actor=people['admin'])
    assert not m.Report.objects.filter(request=row).exists()


def test_applicant_and_bearer_cannot_complete_paper(granted_roles,paper_source,people,client):
    import uuid
    app,row,file,token=paper_source
    payload={'file_id':str(file.pk),'completion_date':timezone.localdate().isoformat(),'expected_version':request_version(row)}
    client.force_login(app.owner)
    with granted_roles('ctm_app',session=True):
        hidden=client.post(f'/api/requests/{row.pk}/paper-completion/',payload,content_type='application/json')
        absent=client.post(f'/api/requests/{uuid.uuid4()}/paper-completion/',payload,content_type='application/json')
        assert hidden.status_code==absent.status_code==404 and hidden.content==absent.content
    client.logout()
    with granted_roles('ctm_app',session=True):
        assert client.post(f'/api/requests/{row.pk}/paper-completion/',payload,content_type='application/json',HTTP_AUTHORIZATION=f'Bearer {token}').status_code==401
    assert not m.Report.objects.filter(request=row).exists()


def test_paper_replay_does_not_replace_source_and_private_helper_denied(granted_roles,paper_source,people):
    from django.db import connection,DatabaseError
    from django.core.exceptions import ValidationError
    _,row,file,_=paper_source
    with granted_roles('ctm_app',people['admin'],session=True):
        report=complete_external_paper(people['admin'],row.pk,file.pk,timezone.localdate().isoformat(),expected_version=request_version(row))
        with pytest.raises(ValidationError):
            complete_external_paper(people['admin'],row.pk,file.pk,(timezone.localdate()-timezone.timedelta(days=1)).isoformat(),expected_version=request_version(row))
    assert m.ReportRevision.objects.get(report=report).answers=={'files':[str(file.pk)]}
    for role in ['ctm_app','ctm_worker']:
        with pytest.raises(DatabaseError,match='permission denied'):
            with granted_roles(role,people['admin']),connection.cursor() as cursor:
                cursor.execute('SELECT public.ctm_paper_file_allowed(%s,%s)',[row.pk,file.pk])


def test_paper_endpoint_receipt_contract_on_each_adapter(paper_source,people,client):
    _,row,file,token=paper_source
    client.force_login(people['admin'])
    payload={'file_id':str(file.pk),'completion_date':timezone.localdate().isoformat(),'expected_version':request_version(row)}
    url=f'/api/requests/{row.pk}/paper-completion/'
    response=client.post(url,payload,content_type='application/json')
    assert response.status_code==201,response.content
    replay=client.post(url,payload,content_type='application/json')
    assert replay.json()==response.json()
    status=client.get(f'/external/reports/{row.pk}/status/',HTTP_AUTHORIZATION=f'Bearer {token}')
    assert status.status_code==200 and status.json()['state']=='completed'
    assert status.json()['receipt']['report_id']==response.json()['id']
    assert m.Report.objects.filter(request=row,method='paper',author=people['admin']).count()==1


def test_exact_paper_receipt_recovers_after_case_closure(granted_roles,paper_source,people):
    from tribunal.services.decisions import withdraw_application
    app,row,file,_=paper_source
    date=timezone.localdate().isoformat();version=request_version(row)
    with granted_roles('ctm_app',people['admin'],session=True):
        report=complete_external_paper(people['admin'],row.pk,file.pk,date,expected_version=version)
    withdraw_application(app.owner,app.pk)
    with granted_roles('ctm_app',people['admin'],session=True):
        replay=complete_external_paper(people['admin'],row.pk,file.pk,date,expected_version=version)
        assert replay.pk==report.pk
    assert m.ReportRevision.objects.filter(report=report).count()==1
