"""Private print transport uses stored wording, never recipient response material."""
import uuid
import pytest
from tribunal import models as m
from tribunal.services.reports import send_request, create_request
from tests.test_core_policy_completion import granted_roles
from tests.test_external_link_projection import priest_request

pytestmark = pytest.mark.django_db


def test_print_escapes_original_wording_and_excludes_capability_and_draft(
        priest_request, people, client, granted_roles):
    app, row = priest_request
    title = 'عنوان <script>alert(1)</script>'
    instructions = 'تعليمات\n<img src="https://example.test/leak">'
    m.ReportRequest.objects.filter(pk=row.pk).update(title=title, instructions=instructions,
        language='ar', saved_response={'testimony': 'SECRET SAVED RESPONSE'})
    token = send_request(people['admin'], row.pk, 'Synthetic Priest', 'secret@example.test')
    row.refresh_from_db()
    client.force_login(people['admin'])
    before = (m.ReportRequest.objects.get(pk=row.pk).state,
              m.AuditEvent.objects.count(), m.Outbox.objects.count(), m.Report.objects.count())
    with granted_roles('ctm_app', session=True):
        response = client.get(f'/api/requests/{row.pk}/print/')
    assert response.status_code == 200, response.content
    text = response.content.decode()
    assert 'lang="ar" dir="rtl"' in text
    assert 'عنوان &lt;script&gt;alert(1)&lt;/script&gt;' in text
    assert '&lt;img src=&quot;https://example.test/leak&quot;&gt;' in text
    assert str(row.pk) in text and app.party.name in text and 'Synthetic Priest' in text
    for private in [token, row.token_hash, 'secret@example.test', 'SECRET SAVED RESPONSE']:
        assert private not in text
    assert text.count('class="line"') == 20
    assert 'no-store' in response['Cache-Control']
    assert response['Referrer-Policy'] == 'no-referrer'
    assert "default-src 'none'" in response['Content-Security-Policy']
    assert before == (m.ReportRequest.objects.get(pk=row.pk).state,
                      m.AuditEvent.objects.count(), m.Outbox.objects.count(), m.Report.objects.count())


@pytest.mark.parametrize('role', ['admin', 'secretary', 'member', 'president', 'applicant'])
def test_print_requires_request_writer(priest_request, people, client, granted_roles, role):
    app, row = priest_request
    client.force_login(app.owner if role == 'applicant' else people[role])
    with granted_roles('ctm_app', session=True):
        result = client.get(f'/api/requests/{row.pk}/print/')
    assert result.status_code == (200 if role in {'admin', 'secretary', 'member'} else 403)


@pytest.mark.parametrize('state', ['completed', 'cancelled', 'closed', 'ordinary'])
def test_print_rejects_inactive_and_other_request_kinds(priest_request, people, client, granted_roles, state):
    app, row = priest_request
    if state == 'closed':
        m.Proceeding.objects.filter(pk=app.proceeding_id).update(status='closed')
    elif state == 'ordinary':
        row = create_request(people['admin'], app.proceeding_id, app.party_id, 'intake', 'Intake', [])
    else:
        m.ReportRequest.objects.filter(pk=row.pk).update(state=state)
    client.force_login(people['admin'])
    with granted_roles('ctm_app', session=True):
        response = client.get(f'/api/requests/{row.pk}/print/')
    assert response.status_code == 422


def test_print_does_not_accept_external_bearer(priest_request, people, client, granted_roles):
    _, row = priest_request
    token = send_request(people['admin'], row.pk, 'Synthetic Priest')
    with granted_roles('ctm_app', session=True):
        assert client.get(f'/api/requests/{row.pk}/print/', HTTP_AUTHORIZATION=f'Bearer {token}').status_code == 401
    client.force_login(people['admin'])
    with granted_roles('ctm_app', session=True):
        assert client.get(f'/api/requests/{uuid.uuid4()}/print/').status_code == 404
        assert client.post(f'/api/requests/{row.pk}/print/').status_code == 405
