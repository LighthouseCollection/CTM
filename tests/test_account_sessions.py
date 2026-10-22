import json
import pytest
from django.contrib.sessions.backends.db import SessionStore
from django.contrib.sessions.models import Session
from django.utils import timezone
from tribunal.models import AuditEvent
from tribunal.services.account_sessions import session_handle
from tests.test_core_policy_completion import granted_roles

pytestmark = pytest.mark.django_db


def stored_session(actor, **overrides):
    store = SessionStore()
    store.update({'_auth_user_id': str(actor.pk),
                  '_auth_user_backend': 'allauth.account.auth_backends.AuthenticationBackend',
                  '_auth_user_hash': actor.get_session_auth_hash(), **overrides})
    store.save()
    return store.session_key


@pytest.mark.parametrize('role', ['applicant', 'member', 'president', 'admin', 'secretary'])
def test_own_sessions_are_safe_and_foreign_handles_are_hidden(granted_roles, people, client, role):
    actor = people[role]
    other = people['applicant' if role != 'applicant' else 'member']
    key = stored_session(actor)
    foreign = stored_session(other)
    client.force_login(actor)
    with granted_roles('ctm_app', session=True):
        result = client.get('/api/account/sessions/')
        assert result.status_code == 200, result.content
        rows = result.json()['items']
        assert len(rows) == 2 and sum(row['current'] for row in rows) == 1
        assert all(set(row) == {'handle', 'current', 'expires_at'} for row in rows)
        assert key not in result.content.decode() and foreign not in result.content.decode()
        assert actor.get_session_auth_hash() not in result.content.decode()
        assert result['Cache-Control'] == 'private, no-store'
        hidden = client.post(f'/api/account/sessions/{session_handle(other, foreign)}/revoke/', '{}', content_type='application/json')
        absent = client.post('/api/account/sessions/' + '0'*64 + '/revoke/', '{}', content_type='application/json')
        assert hidden.status_code == absent.status_code == 404
        assert hidden.content == absent.content
        # Even knowledge of a foreign raw key and an actor-bound handle cannot confer ownership.
        forged = client.post(f'/api/account/sessions/{session_handle(actor, foreign)}/revoke/', '{}', content_type='application/json')
        assert forged.status_code == 404 and forged.content == absent.content
    assert Session.objects.filter(session_key=foreign).exists()


def test_selected_session_revocation_is_retained_and_current_session_survives(granted_roles, people, client):
    actor = people['applicant']
    key = stored_session(actor)
    client.force_login(actor)
    handle = session_handle(actor, key)
    with granted_roles('ctm_app', session=True):
        response = client.post(f'/api/account/sessions/{handle}/revoke/', '{}', content_type='application/json')
        assert response.status_code == 200, response.content
        assert response.json() == {'revoked': True, 'current_session': False}
        assert client.get('/api/session/').status_code == 200
        retry = client.post(f'/api/account/sessions/{handle}/revoke/', '{}', content_type='application/json')
        assert retry.status_code == 404
    assert not Session.objects.filter(session_key=key).exists()
    event = AuditEvent.objects.get(action='account_session_revoked')
    assert event.actor_id == event.source_id == actor.pk
    assert event.metadata == {'session_handle': handle, 'current_session': False}
    assert key not in json.dumps(event.metadata)


def test_current_session_revocation_logs_out_on_next_request(granted_roles, people, client):
    actor = people['applicant']
    client.force_login(actor)
    key = client.session.session_key
    with granted_roles('ctm_app', session=True):
        response = client.post(f'/api/account/sessions/{session_handle(actor,key)}/revoke/', '{}', content_type='application/json')
        assert response.status_code == 200, response.content
        assert response.json()['current_session'] is True
        assert client.get('/api/session/').status_code == 401
    assert not Session.objects.filter(session_key=key).exists()


def test_inventory_excludes_expired_invalid_and_unsupported_sessions(granted_roles, people, client):
    actor = people['applicant']
    expired = stored_session(actor)
    Session.objects.filter(session_key=expired).update(expire_date=timezone.now()-timezone.timedelta(seconds=1))
    bad = stored_session(actor, _auth_user_hash='invalid-hash')
    unsupported = stored_session(actor, _auth_user_backend='unconfigured.backend')
    corrupt = stored_session(actor)
    Session.objects.filter(session_key=corrupt).update(session_data='invalid-signature')
    client.force_login(actor)
    with granted_roles('ctm_app', session=True):
        rows = client.get('/api/account/sessions/').json()['items']
        assert len(rows) == 1 and rows[0]['current']
        for key in [expired, bad, unsupported, corrupt]:
            result = client.post(f'/api/account/sessions/{session_handle(actor,key)}/revoke/', '{}', content_type='application/json')
            assert result.status_code == 404


def test_session_pagination_filters_ownership_before_page(granted_roles, people, client):
    actor = people['applicant']
    for _ in range(4):
        stored_session(people['member'])
        stored_session(actor)
    client.force_login(actor)
    with granted_roles('ctm_app', session=True):
        handles = []
        for offset in [0, 2, 4]:
            response = client.get(f'/api/account/sessions/?offset={offset}&limit=2')
            assert response.status_code == 200, response.content
            page = response.json()
            assert page['next_offset'] == (offset+2 if offset<4 else None)
            handles.extend(row['handle'] for row in page['items'])
        assert len(handles) == len(set(handles)) == 5
        assert client.get('/api/account/sessions/?limit=0').status_code == 422
        assert client.get('/api/account/sessions/?offset=0&offset=1').status_code == 422
        assert client.post('/api/account/sessions/'+'0'*64+'/revoke/', {'account_id':str(people['member'].pk)}, content_type='application/json').status_code == 422


def test_session_management_requires_authentication_and_csrf(people, client):
    from django.test import Client
    assert client.get('/api/account/sessions/').status_code == 401
    assert client.post('/api/account/sessions/'+'0'*64+'/revoke/', '{}', content_type='application/json').status_code == 401
    protected = Client(enforce_csrf_checks=True)
    protected.force_login(people['applicant'])
    assert protected.post('/api/account/sessions/'+'0'*64+'/revoke/', '{}', content_type='application/json').status_code == 403


def test_failed_retained_audit_rolls_back_session_revocation(granted_roles, people, client, monkeypatch):
    from django.core.exceptions import ValidationError
    from tribunal.services import account_sessions
    actor = people['applicant']
    key = stored_session(actor)
    client.force_login(actor)

    def unavailable_audit(*args, **kwargs):
        raise ValidationError('Synthetic retained-audit failure')

    monkeypatch.setattr(account_sessions, 'audit', unavailable_audit)
    with granted_roles('ctm_app', session=True):
        result = client.post(f'/api/account/sessions/{session_handle(actor,key)}/revoke/', '{}', content_type='application/json')
        assert result.status_code == 422
    assert Session.objects.filter(session_key=key).exists()
    assert not AuditEvent.objects.filter(action='account_session_revoked').exists()
