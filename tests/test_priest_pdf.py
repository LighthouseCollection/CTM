"""Real private PDFs, preserved source data and honest renderer failures."""
import subprocess
from unittest.mock import patch
import uuid
import pytest
from tribunal import models as m
from tribunal.services.reports import send_request
from tribunal.priest_pdf_worker import deny_fetch
from tests.test_core_policy_completion import granted_roles
from tests.test_external_link_projection import priest_request

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize('language', ['en', 'ar', 'both'])
def test_real_pdf_retains_wording_and_excludes_private_responses(granted_roles, priest_request, people, client, tmp_path, language):
    app, row = priest_request
    title = 'Synthetic priest request' if language == 'en' else 'طلب تقرير كاهن'
    instructions = 'Saved instructions <script>alert(1)</script>\nتعليمات محفوظة'
    m.ReportRequest.objects.filter(pk=row.pk).update(title=title, instructions=instructions,
        language=language, saved_response={'testimony': 'SECRET SAVED TESTIMONY'})
    token = send_request(people['admin'], row.pk, 'Synthetic Priest', 'secret-priest@example.test')
    row.refresh_from_db()
    before = m.ReportRequest.objects.filter(pk=row.pk).values().get()
    counts = [model.objects.count() for model in [m.Report, m.AuditEvent, m.Attachment, m.Outbox]]
    client.force_login(people['admin'])
    with granted_roles('ctm_app', session=True):
        response = client.get(f'/api/requests/{row.pk}/print.pdf')
    assert response.status_code == 200, response.content
    assert response['Content-Type'] == 'application/pdf'
    assert response.content.startswith(b'%PDF-')
    assert response['Content-Disposition'] == f'attachment; filename="priest-request-{row.pk}.pdf"'
    assert 'no-store' in response['Cache-Control'] and response['Referrer-Policy'] == 'no-referrer'
    file = tmp_path / 'request.pdf'; file.write_bytes(response.content)
    text = subprocess.run(['pdftotext', str(file), '-'], check=True, capture_output=True).stdout.decode()
    assert 'Saved instructions' in text and '<script>alert(1)</script>' in text
    assert 'Synthetic Priest' in text and str(row.pk) in text
    assert any('\u0600' <= char <= '\u06ff' for char in text)
    fonts = subprocess.run(['pdffonts', str(file)], check=True, capture_output=True).stdout
    assert b'DejaVu' in fonts and b'yes yes yes' in fonts
    for secret in [token, row.token_hash, 'secret-priest@example.test', 'SECRET SAVED TESTIMONY']:
        assert secret not in text and secret.encode() not in response.content
    assert m.ReportRequest.objects.filter(pk=row.pk).values().get() == before
    assert counts == [model.objects.count() for model in [m.Report, m.AuditEvent, m.Attachment, m.Outbox]]


@pytest.mark.parametrize('role', ['secretary', 'member', 'president', 'applicant'])
def test_pdf_writer_permissions_match_print_view(granted_roles, priest_request, people, client, role):
    app, row = priest_request
    client.force_login(app.owner if role == 'applicant' else people[role])
    with granted_roles('ctm_app', session=True):
        result = client.get(f'/api/requests/{row.pk}/print.pdf')
    assert result.status_code == (200 if role in {'secretary', 'member'} else 403)


@pytest.mark.parametrize('state', ['completed', 'cancelled', 'closed', 'ordinary'])
def test_pdf_denies_ineligible_source_before_render(granted_roles, priest_request, people, client, state):
    app, row = priest_request
    if state == 'closed':
        m.Proceeding.objects.filter(pk=app.proceeding_id).update(status='closed')
    elif state == 'ordinary':
        from tribunal.services.reports import create_request
        row = create_request(people['admin'], app.proceeding_id, app.party_id, 'intake', 'Intake', [])
    else:
        m.ReportRequest.objects.filter(pk=row.pk).update(state=state)
    client.force_login(people['admin'])
    with patch('tribunal.services.priest_pdf.subprocess.run') as render:
        with granted_roles('ctm_app', session=True):
            response = client.get(f'/api/requests/{row.pk}/print.pdf')
        assert response.status_code == 422
        render.assert_not_called()


@pytest.mark.parametrize('failure', ['missing', 'timeout', 'crash', 'bad_output'])
def test_renderer_failure_is_503_and_does_not_publish_or_log_document(granted_roles, priest_request, people, client, failure):
    _, row = priest_request
    client.force_login(people['admin'])
    effects = {'missing': OSError('synthetic dependency unavailable'),
               'timeout': subprocess.TimeoutExpired('synthetic-renderer', 30),
               'crash': subprocess.CalledProcessError(1, 'synthetic-renderer')}
    kwargs = {'side_effect': effects[failure]} if failure != 'bad_output' else {
        'return_value': subprocess.CompletedProcess([], 0, stdout=b'not a PDF')}
    with patch('tribunal.services.priest_pdf.subprocess.run', **kwargs):
        with granted_roles('ctm_app', session=True):
            response = client.get(f'/api/requests/{row.pk}/print.pdf')
    assert response.status_code == 503 and response.json()['error'] == 'pdf_unavailable'
    assert 'no-store' in response['Cache-Control']
    assert not m.Report.objects.filter(request=row).exists()
    assert m.ReportRequest.objects.get(pk=row.pk).state == 'draft'


def test_large_complete_request_is_not_truncated(granted_roles, priest_request, people, client):
    _, row = priest_request
    m.ReportRequest.objects.filter(pk=row.pk).update(instructions='&' * 110_000)
    client.force_login(people['admin'])
    with patch('tribunal.services.priest_pdf.subprocess.run') as render:
        with granted_roles('ctm_app', session=True):
            response = client.get(f'/api/requests/{row.pk}/print.pdf')
        assert response.status_code == 422
        render.assert_not_called()
    assert m.ReportRequest.objects.get(pk=row.pk).instructions == '&' * 110_000


def test_pdf_requires_session_and_never_accepts_capability(granted_roles, priest_request, people, client):
    _, row = priest_request
    token = send_request(people['admin'], row.pk, 'Synthetic Priest')
    with granted_roles('ctm_app', session=True):
        assert client.get(f'/api/requests/{row.pk}/print.pdf', HTTP_AUTHORIZATION=f'Bearer {token}').status_code == 401
    client.force_login(people['admin'])
    with granted_roles('ctm_app', session=True):
        assert client.get(f'/api/requests/{uuid.uuid4()}/print.pdf').status_code == 404
        assert client.post(f'/api/requests/{row.pk}/print.pdf').status_code == 405


@pytest.mark.parametrize('url', ['https://example.test/source', 'http://127.0.0.1/private',
    'file:///etc/passwd', 'data:text/plain,private'])
def test_pdf_fetcher_denies_every_resource_scheme(url):
    with pytest.raises(ValueError):
        deny_fetch(url)


def test_pdf_http_contract_across_adapters(priest_request, people, client):
    _, row = priest_request
    client.force_login(people['admin'])
    response = client.get(f'/api/requests/{row.pk}/print.pdf')
    assert response.status_code == 200 and response.content.startswith(b'%PDF-')
