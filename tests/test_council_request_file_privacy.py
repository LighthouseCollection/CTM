"""External-priest/interview originals stay council-only, including legacy rows."""
import uuid
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import DatabaseError
from tribunal import models as m
from tribunal.services.applications import submit_application
from tribunal.services.reports import create_request, send_request
from tribunal.services.files import private_path
from tests.test_core_policy_completion import granted_roles

pytestmark = pytest.mark.django_db


@pytest.fixture
def request_case(ready_application, people):
    app = ready_application
    submit_application(app.owner, app.pk, 'council-file-privacy', {'accepted':True,'name':'John Smith'})
    app.refresh_from_db()
    return app


def sent_request(app, people, kind):
    request = create_request(people['admin'],app.proceeding_id,app.party_id,kind,'Synthetic request',[])
    send_request(people['admin'],request.pk,external_name='Synthetic priest')
    return request


@pytest.mark.parametrize('kind',['external_priest','interview'])
@pytest.mark.parametrize('category',['EVD','REC'])
def test_council_upload_never_grants_subject_download(granted_roles, request_case, people, client, settings, tmp_path, monkeypatch, django_capture_on_commit_callbacks, kind, category):
    settings.MEDIA_ROOT = tmp_path
    app = request_case
    request = sent_request(app, people, kind)
    monkeypatch.setattr('tribunal.services.files.scan', lambda data:'clean')
    payload = b'%PDF-synthetic original' if category=='EVD' else b'RIFF0000WAVEsynthetic recording'
    client.force_login(people['admin'])
    with granted_roles('ctm_app',session=True), django_capture_on_commit_callbacks(execute=True):
        uploaded = client.post('/api/files/',{'request_id':str(request.pk),'category':category,'file':SimpleUploadedFile('synthetic.bin',payload)})
        assert uploaded.status_code == 201, uploaded.content
    file = m.FileVersion.objects.get(pk=uploaded.json()['id'])
    url = f'/api/files/{file.pk}/'
    client.force_login(app.owner)
    with granted_roles('ctm_app',session=True):
        hidden = client.get(url)
        absent = client.get(f'/api/files/{uuid.uuid4()}/')
        assert hidden.status_code == absent.status_code == 404
        assert hidden.content == absent.content
        assert client.head(url).status_code == 404
        assert client.get(url,HTTP_RANGE='bytes=0-3').status_code == 404
        assert not m.Attachment.objects.filter(pk=file.attachment_id).exists()
        assert not m.FileVersion.objects.filter(pk=file.pk).exists()
    assert file.attachment.owner_id is None and file.attachment.visibility=='council'
    client.force_login(people['member'])
    with granted_roles('ctm_app',session=True):
        visible = client.get(url,HTTP_RANGE='bytes=0-3')
        assert visible.status_code == 206, visible.content if not visible.streaming else ''
        assert b''.join(visible.streaming_content)==payload[:4]


@pytest.mark.parametrize('kind',['external_priest','interview'])
def test_legacy_wrongly_owned_original_and_derived_text_are_hidden(granted_roles, request_case, people, client, settings, tmp_path, kind):
    settings.MEDIA_ROOT = tmp_path
    app = request_case
    request = sent_request(app,people,kind)
    attachment = m.Attachment.objects.create(case=app.case,proceeding=app.proceeding,report_request=request,owner=app.owner,visibility='own',category='EVD')
    file = m.FileVersion.objects.create(attachment=attachment,number=1,object_key=f'legacy/{attachment.pk}.pdf',original_name='private.pdf',display_name='private.pdf',mime_type='application/pdf',byte_count=5,sha256='a'*64,actor=people['admin'])
    scan = m.FileTechnicalEvent.objects.create(file=file,task='scan',result='clean')
    text = m.DocumentText.objects.create(file=file,engine='synthetic',text='PRIVATE PRIEST ORIGINAL')
    path = private_path(file.object_key);path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b'%PDF-')
    client.force_login(app.owner)
    with granted_roles('ctm_app',session=True):
        assert client.get(f'/api/files/{file.pk}/').status_code == 404
        for model, pk in [(m.Attachment,attachment.pk),(m.FileVersion,file.pk),(m.FileTechnicalEvent,scan.pk),(m.DocumentText,text.pk)]:
            from tribunal.db.context import database_actor
            with database_actor(app.owner):
                assert not model.objects.filter(pk=pk).exists()
    # Retained source data is not rewritten as a historical backfill.
    attachment.refresh_from_db()
    assert attachment.owner_id==app.owner_id and attachment.visibility=='own'
    client.force_login(people['admin'])
    with granted_roles('ctm_app',session=True):
        visible = client.get(f'/api/files/{file.pk}/')
        assert visible.status_code == 200
        assert b''.join(visible.streaming_content)==b'%PDF-'


@pytest.mark.parametrize('kind',['external_priest','interview'])
@pytest.mark.parametrize('forgery',['own_visibility','applicant_owner','missing_council_visibility','application_binding'])
def test_raw_app_role_cannot_forge_request_attachment_scope(granted_roles, request_case, people, kind, forgery):
    app = request_case
    request = sent_request(app,people,kind)
    values = dict(case=app.case,proceeding=app.proceeding,report_request=request,owner=None,visibility='council',category='EVD')
    if forgery=='own_visibility':
        values.update(owner=app.owner,visibility='own')
    elif forgery=='applicant_owner':
        values['owner']=app.owner
    elif forgery=='missing_council_visibility':
        values['visibility']='own'
    else:
        values.update(application=app,owner=app.owner)
    with pytest.raises(DatabaseError):
        with granted_roles('ctm_app',people['admin']):
            m.Attachment.objects.create(**values)
    assert not m.Attachment.objects.filter(report_request=request).exists()


@pytest.mark.parametrize('kind',['external_priest','interview'])
def test_service_denies_legacy_subject_even_without_rls_concealment(request_case, people, kind):
    from django.core.exceptions import PermissionDenied
    from tribunal.services.files import authorized_file
    app = request_case
    request = sent_request(app,people,kind)
    attachment = m.Attachment.objects.create(case=app.case,proceeding=app.proceeding,report_request=request,owner=app.owner,visibility='own',category='EVD')
    file = m.FileVersion.objects.create(attachment=attachment,number=1,object_key=f'legacy/{attachment.pk}.pdf',original_name='private.pdf',display_name='private.pdf',mime_type='application/pdf',byte_count=5,sha256='a'*64,actor=people['admin'])
    with pytest.raises(PermissionDenied,match='council-only'):
        authorized_file(app.owner,file.pk,require_safe=False)


def test_ordinary_intake_original_still_belongs_to_subject(granted_roles, request_case, people, client, settings, tmp_path, monkeypatch, django_capture_on_commit_callbacks):
    settings.MEDIA_ROOT=tmp_path
    app=request_case
    request=sent_request(app,people,'intake')
    monkeypatch.setattr('tribunal.services.files.scan',lambda data:'clean')
    client.force_login(people['admin'])
    with granted_roles('ctm_app',session=True),django_capture_on_commit_callbacks(execute=True):
        response=client.post('/api/files/',{'request_id':str(request.pk),'category':'EVD','file':SimpleUploadedFile('synthetic.pdf',b'%PDF-intake')})
        assert response.status_code==201,response.content
    file=m.FileVersion.objects.get(pk=response.json()['id'])
    assert file.attachment.owner_id==app.owner_id and file.attachment.visibility=='own'
    client.force_login(app.owner)
    with granted_roles('ctm_app',session=True):
        delivered=client.get(f'/api/files/{file.pk}/')
        assert delivered.status_code==200
        assert b''.join(delivered.streaming_content)==b'%PDF-intake'


@pytest.mark.parametrize('method',['get','post','put'])
def test_unavailable_external_link_never_sends_referrer(client,method):
    response=getattr(client,method)(f'/external/reports/{uuid.uuid4()}/')
    assert response.status_code in {403,405}
    assert response['Referrer-Policy']=='no-referrer'
    assert response['Cache-Control']=='private, no-store'


@pytest.mark.django_db(transaction=True)
def test_policy_upgrade_and_reverse_preserve_strict_medical_consent(granted_roles, request_case, people):
    from django.db import connection
    from django.db.migrations.executor import MigrationExecutor
    app=request_case
    request=sent_request(app,people,'medical')
    attachment=m.Attachment.objects.create(case=app.case,proceeding=app.proceeding,report_request=request,owner=app.owner,visibility='medical',category='REPORT')
    file=m.FileVersion.objects.create(attachment=attachment,number=1,object_key=f'legacy-medical/{attachment.pk}.pdf',original_name='private.pdf',display_name='private.pdf',mime_type='application/pdf',byte_count=5,sha256='a'*64,actor=app.owner)
    m.FileTechnicalEvent.objects.create(file=file,task='scan',result='clean')
    m.MedicalRelease.objects.create(request=request,subject=app.owner,signature=file,
        declaration=m.QuestionnaireVersion.objects.get(purpose='medical_release'),scope={'council':'true'})
    try:
        for leaf in ['0042_council_request_file_privacy','0041_bound_returned_filing']:
            MigrationExecutor(connection).migrate([('tribunal',leaf)])
            with granted_roles('ctm_app',people['admin']):
                assert not m.FileVersion.objects.filter(pk=file.pk).exists()
    finally:
        MigrationExecutor(connection).migrate([('tribunal','0051_runtime_settings_consumers')])
