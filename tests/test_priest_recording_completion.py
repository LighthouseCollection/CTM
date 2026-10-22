"""Council recording source completion under actual SQL app authorization."""
from unittest.mock import patch
import pytest
from django.db import DatabaseError
from django.utils import timezone
from tribunal import models as m
from tribunal.db.context import database_settings
from tribunal.services.reports import send_request, revise_report
from tribunal.services.priest_recording import complete_priest_recording
from tribunal.services.request_contracts import request_version
from tests.test_core_policy_completion import granted_roles
from tests.test_external_link_projection import priest_request

pytestmark = pytest.mark.django_db


@pytest.fixture
def recording_source(priest_request, people, settings, tmp_path):
    app, row = priest_request
    settings.MEDIA_ROOT = tmp_path
    token = send_request(people['admin'], row.pk, 'Synthetic Priest')
    row.refresh_from_db()
    attachment = m.Attachment.objects.create(case=app.case, proceeding=app.proceeding,
        owner=None, visibility='council', category='AUDIO')
    file = m.FileVersion.objects.create(attachment=attachment, number=1,
        object_key=f'recording/{attachment.pk}.mp3', original_name='recording.mp3', display_name='recording.mp3',
        mime_type='audio/mpeg', byte_count=3, sha256='a'*64, actor=people['admin'])
    m.FileTechnicalEvent.objects.create(file=file, task='scan', result='clean')
    from tribunal.services.files import private_path
    path = private_path(file.object_key); path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(b'ID3')
    return app, row, file, token


def payload(row, file):
    return {'file_id': str(file.pk), 'completion_date': timezone.localdate().isoformat(),
            'recording_notice': {'acknowledged': True}, 'duration_ms': 1200,
            'expected_version': request_version(row)}


def test_runtime_completion_retains_actual_recorder_and_queues_only(granted_roles, recording_source, people, client):
    app, row, file, token = recording_source
    client.force_login(people['admin']); data = payload(row, file)
    url = f'/api/requests/{row.pk}/recording-completion/'
    with granted_roles('ctm_app', session=True):
        response = client.post(url, data, content_type='application/json')
        assert response.status_code == 201, response.content
        assert client.post(url, data, content_type='application/json').json() == response.json()
        listed = client.get(f'/api/reports/{response.json()["id"]}/recordings/')
        assert listed.status_code == 200, listed.content
        item = listed.json()['items'][0]
        assert item['captured_by'] == str(people['admin'].pk)
        assert item['processing']['state'] == 'queued' and item['transcripts'] == []
        assert item['download_url'] == f'/api/files/{file.pk}/'
        original = client.get(item['download_url'])
        assert b''.join(original.streaming_content) == b'ID3'
        reports = client.get(f'/api/cases/{app.case_id}/reports/').json()['items']
        assert reports[0]['method'] == 'recording' and reports[0]['can_revise'] is False
    report = m.Report.objects.get(pk=response.json()['id'])
    recording = m.Recording.objects.get(pk=response.json()['recording_id'])
    assert report.author_id == recording.captured_by_id == people['admin'].pk
    assert recording.notice_recorded and recording.finalized_at and recording.duration_ms == 1200
    assert report.revisions.get().answers == {'files': [str(file.pk)]}
    assert report.revisions.get().actor_id == people['admin'].pk
    assert m.ProcessingRun.objects.get(file=file).state == 'queued'
    assert m.Outbox.objects.filter(kind='transcribe', case=app.case).count() == 1
    assert m.AuditEvent.objects.filter(action='external_recording_report_submitted', source_id=report.pk).count() == 1
    assert not m.TranscriptRevision.objects.filter(recording=recording).exists()
    client.logout()
    with granted_roles('ctm_app', session=True):
        assert client.get(f'/external/reports/{row.pk}/', HTTP_AUTHORIZATION=f'Bearer {token}').status_code == 403
        status = client.get(f'/external/reports/{row.pk}/status/', HTTP_AUTHORIZATION=f'Bearer {token}')
        assert status.status_code == 200 and status.json()['receipt']['report_id'] == str(report.pk)
    client.force_login(app.owner)
    with granted_roles('ctm_app', session=True):
        assert client.get(f'/api/reports/{report.pk}/recordings/').status_code == 403
        assert client.get(f'/api/files/{file.pk}/').status_code == 404


@pytest.mark.parametrize('bad', ['pending', 'stale', 'wrong_scope', 'notice', 'notice_nan', 'notice_null', 'duration', 'future', 'version', 'unassigned'])
def test_reject_invalid_source_without_partial_completion(granted_roles, recording_source, people, client, bad):
    _, row, file, _ = recording_source
    data = payload(row, file); actor = people['admin']
    if bad == 'pending':
        m.FileTechnicalEvent.objects.create(file=file, task='scan', result='pending')
    elif bad == 'stale':
        m.FileVersion.objects.create(attachment=file.attachment, number=2, object_key='recording/new.mp3',
            mime_type='audio/mpeg', byte_count=3, sha256='b'*64, actor=actor)
    elif bad == 'wrong_scope':
        other = m.Attachment.objects.create(case=row.case, proceeding=row.proceeding, report_request=row,
            owner=None, visibility='council', category='AUDIO')
        file = m.FileVersion.objects.create(attachment=other, number=1, object_key='recording/request-bound.mp3',
            mime_type='audio/mpeg', byte_count=3, sha256='b'*64, actor=actor)
        m.FileTechnicalEvent.objects.create(file=file, task='scan', result='clean'); data['file_id'] = str(file.pk)
    elif bad == 'notice': data['recording_notice'] = {'acknowledged': 'true'}
    elif bad == 'notice_nan': data['recording_notice'] = {'acknowledged': True, 'duration': float('nan')}
    elif bad == 'notice_null': data['recording_notice'] = {'acknowledged': True, 'detail': '\x00'}
    elif bad == 'duration': data['duration_ms'] = True
    elif bad == 'future': data['completion_date'] = (timezone.localdate()+timezone.timedelta(days=1)).isoformat()
    elif bad == 'version': data['expected_version'] = 'stale'
    elif bad == 'unassigned': actor = people['president']
    client.force_login(actor)
    with granted_roles('ctm_app', session=True):
        result = client.post(f'/api/requests/{row.pk}/recording-completion/', data, content_type='application/json')
    assert result.status_code in {403, 422}, result.content
    assert m.ReportRequest.objects.get(pk=row.pk).state == 'sent'
    assert not m.Report.objects.filter(request=row).exists()
    assert not m.Recording.objects.filter(file=file).exists()
    assert not m.ProcessingRun.objects.filter(file=file).exists()


def test_audit_failure_rolls_back_entire_recording_submission(granted_roles, recording_source, people):
    _, row, file, _ = recording_source
    with pytest.raises(RuntimeError):
        with granted_roles('ctm_app', people['admin'], session=True):
            with patch('tribunal.services.priest_recording.audit', side_effect=RuntimeError('synthetic audit failure')):
                complete_priest_recording(people['admin'], row.pk, **payload(row, file))
    assert not m.Report.objects.filter(request=row).exists()
    assert not m.Recording.objects.filter(file=file).exists()
    assert not m.ProcessingRun.objects.filter(file=file).exists()


@pytest.mark.parametrize('bad', ['method', 'author', 'source', 'date'])
def test_raw_recording_report_forgeries_are_denied(granted_roles, recording_source, people, bad):
    _, row, file, _ = recording_source
    ctx = {'ctm.recording_request': str(row.pk), 'ctm.recording_file': str(file.pk),
           'ctm.recording_date': timezone.localdate().isoformat(), 'ctm.recording_acknowledged': 'true'}
    if bad == 'source': ctx['ctm.recording_file'] = str(row.pk)
    if bad == 'date': ctx['ctm.recording_date'] = (timezone.localdate()+timezone.timedelta(days=1)).isoformat()
    values = {'request': row, 'author': people['admin'], 'method': 'recording'}
    if bad == 'method': ctx = {}
    if bad == 'author': values['author'] = people['member']
    with pytest.raises(DatabaseError):
        with granted_roles('ctm_app', people['admin'], session=True):
            with database_settings(ctx):
                m.Report.objects.create(**values)


def test_recording_http_contract_across_adapters(recording_source, people, client):
    _, row, file, _ = recording_source
    client.force_login(people['admin'])
    result = client.post(f'/api/requests/{row.pk}/recording-completion/', payload(row, file), content_type='application/json')
    assert result.status_code == 201, result.content


@pytest.mark.parametrize('bad', ['number', 'answers', 'observations', 'actor'])
def test_raw_initial_revision_must_match_recorded_original(granted_roles, recording_source, people, bad):
    _, row, file, _ = recording_source
    ctx = {'ctm.recording_request': str(row.pk), 'ctm.recording_file': str(file.pk),
           'ctm.recording_date': timezone.localdate().isoformat(), 'ctm.recording_acknowledged': 'true'}
    values = {'number': 1, 'answers': {'files': [str(file.pk)]}, 'observations': '', 'actor': people['admin']}
    if bad == 'number': values['number'] = 2
    elif bad == 'answers': values['answers'] = {'text': 'Forged source text'}
    elif bad == 'observations': values['observations'] = 'Forged observation'
    elif bad == 'actor': values['actor'] = people['member']
    with pytest.raises(DatabaseError):
        with granted_roles('ctm_app', people['admin'], session=True):
            with database_settings(ctx):
                report = m.Report.objects.create(request=row, author=people['admin'], method='recording')
                m.ReportRevision.objects.create(report=report, **values)


@pytest.mark.parametrize('bad', ['recorder', 'notice', 'notice_type'])
def test_raw_capture_cannot_invent_actor_or_notice(granted_roles, recording_source, people, bad):
    _, row, file, _ = recording_source
    ctx = {'ctm.recording_request': str(row.pk), 'ctm.recording_file': str(file.pk),
           'ctm.recording_date': timezone.localdate().isoformat(), 'ctm.recording_acknowledged': 'true'}
    values = {'file': file, 'captured_by': people['admin'], 'notice_recorded': True,
              'recording_notice': {'acknowledged': True}}
    if bad == 'recorder': values['captured_by'] = people['member']
    elif bad == 'notice': values['notice_recorded'] = False
    elif bad == 'notice_type': values['recording_notice'] = {'acknowledged': 'true'}
    with pytest.raises(DatabaseError):
        with granted_roles('ctm_app', people['admin'], session=True):
            with database_settings(ctx):
                report = m.Report.objects.create(request=row, author=people['admin'], method='recording')
                m.ReportRevision.objects.create(report=report, number=1, answers={'files': [str(file.pk)]}, actor=people['admin'])
                m.Recording.objects.create(report=report, **values)


def test_exact_recovery_after_closure_and_rewrite_denial(granted_roles, recording_source, people, client):
    app, row, file, _ = recording_source
    data = payload(row, file); url = f'/api/requests/{row.pk}/recording-completion/'
    client.force_login(people['admin'])
    with granted_roles('ctm_app', session=True):
        first = client.post(url, data, content_type='application/json')
        assert first.status_code == 201, first.content
    m.Proceeding.objects.filter(pk=app.proceeding_id).update(status='closed')
    m.Case.objects.filter(pk=app.case_id).update(status='closed')
    with granted_roles('ctm_app', session=True):
        replay = client.post(url, data, content_type='application/json')
        assert replay.status_code == 201 and replay.json() == first.json()
        assert client.post(url, {**data, 'duration_ms': 1300}, content_type='application/json').status_code == 422
    from django.core.exceptions import PermissionDenied
    with pytest.raises(PermissionDenied):
        with granted_roles('ctm_app', people['admin'], session=True):
            revise_report(people['admin'], first.json()['id'], {'text': 'Replacement'}, expected_version=1)


@pytest.mark.parametrize('role', ['ctm_app', 'ctm_worker'])
def test_private_recording_helpers_have_no_direct_runtime_grant(granted_roles, people, role):
    from django.db import connection
    with granted_roles(role, people['admin'], session=True):
        with connection.cursor() as cursor:
            for function in ['ctm_recording_file_allowed(uuid,uuid)', 'ctm_recording_capture_allowed(jsonb,text)']:
                cursor.execute('SELECT has_function_privilege(current_user,%s,%s)', [function, 'EXECUTE'])
                assert cursor.fetchone() == (False,)
