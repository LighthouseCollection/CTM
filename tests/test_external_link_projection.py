"""Council link lifecycle display must not disclose the capability to readers."""
import pytest
from django.utils import timezone
from tribunal import models as m
from tribunal.services.applications import submit_application
from tribunal.services.council import assign_case
from tribunal.services.reports import create_request, send_request, complete_external, cancel_request
from tribunal.services.request_contracts import request_version
from tests.test_core_policy_completion import granted_roles

pytestmark = pytest.mark.django_db


@pytest.fixture
def priest_request(ready_application, people):
    app = ready_application
    submit_application(app.owner, app.pk, 'link-projection', {'accepted': True, 'name': 'John Smith'})
    app.refresh_from_db()
    assign_case(people['admin'], app.case_id, people['member'].pk, people['president'].pk)
    row = create_request(people['admin'], app.proceeding_id, app.party_id,
        'external_priest', 'Synthetic priest report', [], instructions='Private instructions')
    return app, row


def read_row(client, granted_roles, actor, app, row):
    client.force_login(actor)
    with granted_roles('ctm_app', session=True):
        response = client.get(f'/api/cases/{app.case_id}/requests/')
        assert response.status_code == 200, response.content
        return next(item for item in response.json()['items'] if item['id'] == str(row.pk)), response


@pytest.mark.parametrize('state', ['not_issued', 'active', 'expired', 'completed', 'cancelled', 'closed', 'closed_case', 'unavailable'])
def test_council_sees_authoritative_link_lifecycle(granted_roles, priest_request, people, client, state):
    app, row = priest_request
    token = ''
    if state != 'not_issued':
        token = send_request(people['admin'], row.pk, 'Synthetic Priest', 'private-priest@example.test')
    if state == 'expired':
        m.ReportRequest.objects.filter(pk=row.pk).update(expires_at=timezone.now()-timezone.timedelta(seconds=1))
    elif state == 'completed':
        complete_external(row.pk, token, {'testimony': 'Private original'})
    elif state == 'cancelled':
        row.refresh_from_db()
        cancel_request(people['admin'], row.pk, request_version(row))
    elif state == 'closed':
        m.Proceeding.objects.filter(pk=app.proceeding_id).update(status='closed')
    elif state == 'closed_case':
        m.Case.objects.filter(pk=app.case_id).update(status='closed')
    elif state == 'unavailable':
        m.ReportRequest.objects.filter(pk=row.pk).update(token_hash='')
    row.refresh_from_db()
    item, response = read_row(client, granted_roles, people['admin'], app, row)
    link = item['external_link']
    assert link == {
        'priest_name': '' if state == 'not_issued' else 'Synthetic Priest',
        'expires_at': row.expires_at.isoformat() if row.expires_at else None,
        'state': 'closed' if state == 'closed_case' else state,
        'can_issue': state == 'not_issued',
        'can_reissue': state in {'active', 'expired', 'unavailable'},
        'can_cancel': state in {'not_issued', 'active', 'expired', 'unavailable'},
    }
    assert item['request_version'] == request_version(row)
    for secret in ['token_hash', 'external_email', 'saved_response', 'private-priest@example.test', 'Private original']:
        assert secret not in response.content.decode()
    if token:
        assert token not in response.content.decode()
    assert 'no-store' in response['Cache-Control']


@pytest.mark.parametrize('role', ['admin', 'secretary', 'member', 'president', 'unassigned'])
def test_link_controls_match_writer_authority(granted_roles, priest_request, people, client, role):
    app, row = priest_request
    actor = people[role] if role != 'unassigned' else m.Account.objects.create_user(
        email='unassigned-projection@example.test', role='member', email_verified=True)
    item, _ = read_row(client, granted_roles, actor, app, row)
    link = item['external_link']
    assert link['state'] == 'not_issued'
    assert link['can_issue'] == link['can_cancel'] == (role in {'admin', 'secretary', 'member'})
    assert link['can_reissue'] is False


def test_link_projection_stays_hidden_from_applicants_and_ordinary_requests(granted_roles, priest_request, people, client):
    app, row = priest_request
    send_request(people['admin'], row.pk, 'Synthetic Priest', 'private-priest@example.test')
    ordinary = create_request(people['admin'], app.proceeding_id, app.party_id, 'intake', 'Own intake', [])
    send_request(people['admin'], ordinary.pk)
    for actor in [people['admin'], app.owner]:
        item, response = read_row(client, granted_roles, actor, app, ordinary)
        assert 'external_link' not in item
        if actor == app.owner:
            assert str(row.pk) not in response.content.decode()
            assert 'Synthetic Priest' not in response.content.decode()
    outsider = m.Account.objects.create_user(email='projection-outsider@example.test', email_verified=True)
    client.force_login(outsider)
    with granted_roles('ctm_app', session=True):
        assert client.get(f'/api/cases/{app.case_id}/requests/').status_code == 404


def test_reissue_updates_expiry_without_returning_capability_in_list(granted_roles, priest_request, people, client):
    app, row = priest_request
    old = send_request(people['admin'], row.pk, 'Old Priest', 'old@example.test')
    m.ReportRequest.objects.filter(pk=row.pk).update(expires_at=timezone.now()-timezone.timedelta(days=1))
    token = send_request(people['admin'], row.pk, 'Current Priest', 'current@example.test')
    item, response = read_row(client, granted_roles, people['member'], app, row)
    assert item['external_link']['state'] == 'active'
    assert item['external_link']['priest_name'] == 'Current Priest'
    assert item['external_link']['can_reissue'] is True
    assert old not in response.content.decode() and token not in response.content.decode()
    with granted_roles('ctm_app', session=True):
        assert client.get(f'/external/reports/{row.pk}/', HTTP_AUTHORIZATION=f'Bearer {old}').status_code == 403
        assert client.get(f'/external/reports/{row.pk}/', HTTP_AUTHORIZATION=f'Bearer {token}').status_code == 200
