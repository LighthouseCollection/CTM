import uuid
import pytest
from django.utils import timezone
from tribunal.models import Account, Tribunal, StaffMembership, StaffRole, AuditEvent
from tribunal.services.staff_roles import create_tribunal, grant_assignment_authority, revoke_assignment_authority
from tests.test_core_policy_completion import granted_roles

pytestmark = pytest.mark.django_db


@pytest.fixture
def appointment(granted_roles, people, settings):
    with granted_roles('ctm_app', people['admin']):
        tribunal = create_tribunal(people['admin'], 'fixture-tribunal', 'Synthetic institution')
    settings.CTM_TRIBUNAL_ID = str(tribunal.pk)
    with granted_roles('ctm_app', people['admin']):
        role = grant_assignment_authority(people['admin'], people['member'].pk, tribunal.pk)
    return tribunal, role


@pytest.mark.parametrize('viewer', ['admin','secretary'])
def test_actual_appointment_and_grant_projection(granted_roles, appointment, people, client, viewer):
    tribunal, role = appointment
    member = people['member']
    client.force_login(people[viewer])
    before = AuditEvent.objects.count()
    with granted_roles('ctm_app', session=True):
        response = client.get(f'/api/system/accounts/{member.pk}/memberships/')
        assert response.status_code == 200, response.content
        result = response.json()
        assert result['account_role'] == 'member' and result['account_active'] is True
        row = result['items'][0]
        assert row['id'] == str(role.membership_id)
        assert row['appointed_by_id'] == str(people['admin'].pk)
        assert row['tribunal']['id'] == str(tribunal.pk)
        assert row['assignment_scope_current'] is True
        grants = client.get(f'/api/system/accounts/{member.pk}/role-history/').json()['items']
        assert grants[0]['role'] == 'president'
        assert grants[0]['granted_by_id'] == str(people['admin'].pk)
        assert grants[0]['assignment_authority_current'] is True
        assert grants[0]['revocation_event'] is None
        assert response['Cache-Control'] == 'private, no-store'
        for forbidden in ['microsoft_subject','password','person_id','email','phone','portrait']:
            assert forbidden not in result
    assert AuditEvent.objects.count() == before
    member.refresh_from_db()
    assert member.role == 'member'


def test_actual_revocation_actor_is_retained(granted_roles, appointment, people, client):
    _, role = appointment
    with granted_roles('ctm_app', people['admin']):
        revoke_assignment_authority(people['admin'], role.pk)
    event = AuditEvent.objects.get(source_id=role.pk, action='assignment_authority_revoked')
    client.force_login(people['secretary'])
    with granted_roles('ctm_app', session=True):
        row = client.get(f"/api/system/accounts/{people['member'].pk}/role-history/").json()['items'][0]
        assert row['assignment_authority_current'] is False
        assert row['revoked_at'] is not None
        assert row['revocation_event'] == {'id':str(event.pk), 'actor_id':str(people['admin'].pk), 'timestamp':event.created_at.isoformat()}
        assert row['granted_by_id'] == str(people['admin'].pk)


@pytest.mark.parametrize('condition',['inactive','ended','future','different_scope','missing_scope'])
def test_history_retained_when_assignment_scope_is_not_current(granted_roles, appointment, people, client, settings, condition):
    tribunal, role = appointment
    member = people['member']
    if condition == 'inactive':
        member.is_active = False
        member.save(update_fields=['is_active'])
    elif condition in {'ended','future'}:
        now = timezone.now()
        start = now-timezone.timedelta(days=2) if condition == 'ended' else now+timezone.timedelta(days=1)
        membership = StaffMembership.objects.create(account=member, tribunal=tribunal, appointed_by=people['admin'], active_from=start,
            active_until=now-timezone.timedelta(days=1) if condition=='ended' else None)
        role = StaffRole.objects.create(membership=membership,role='secretary',granted_by=people['admin'])
    else:
        settings.CTM_TRIBUNAL_ID = str(uuid.uuid4()) if condition=='different_scope' else ''
    client.force_login(people['secretary'])
    with granted_roles('ctm_app', session=True):
        result = client.get(f'/api/system/accounts/{member.pk}/memberships/')
        assert result.status_code == 200, result.content
        row = next(row for row in result.json()['items'] if row['id']==str(role.membership_id))
        assert row['assignment_scope_current'] is False
        grant = next(row for row in client.get(f'/api/system/accounts/{member.pk}/role-history/').json()['items'] if row['id']==str(role.pk))
        assert grant['assignment_authority_current'] is False


def test_missing_legacy_provenance_is_not_invented(granted_roles, appointment, people, client):
    _, role = appointment
    role.revoked_at = timezone.now()
    role.save(update_fields=['revoked_at'])
    client.force_login(people['admin'])
    with granted_roles('ctm_app', session=True):
        row = client.get(f"/api/system/accounts/{people['member'].pk}/role-history/").json()['items'][0]
        assert row['revoked_at'] is not None and row['revocation_event'] is None
        # Base Account.role is current state, not a synthetic historical grant.
        baseline = client.get(f"/api/system/accounts/{people['president'].pk}/role-history/").json()
        assert baseline['account_role'] == 'president' and baseline['items'] == []


@pytest.mark.parametrize('suffix',['memberships/','role-history/'])
def test_member_history_authority_and_hidden_target(granted_roles, people, client, suffix):
    route = f"/api/system/accounts/{people['member'].pk}/{suffix}"
    assert client.get(route).status_code == 401
    for actor in [people['applicant'],people['member'],people['president']]:
        client.force_login(actor)
        with granted_roles('ctm_app',session=True):
            assert client.get(route).status_code == 403
    client.force_login(people['secretary'])
    with granted_roles('ctm_app',session=True):
        applicant = client.get(f"/api/system/accounts/{people['applicant'].pk}/{suffix}")
        absent = client.get(f'/api/system/accounts/{uuid.uuid4()}/{suffix}')
        assert applicant.status_code == absent.status_code == 404
        assert applicant.content == absent.content
        assert client.post(route,{},content_type='application/json').status_code == 405


def test_member_history_pagination_reaches_all_retained_rows(granted_roles, people, client, settings):
    tribunal = Tribunal.objects.create(code='history-fixture',name_en='Synthetic institution')
    settings.CTM_TRIBUNAL_ID = str(tribunal.pk)
    now = timezone.now()
    for i in range(53):
        membership = StaffMembership.objects.create(account=people['member'],tribunal=tribunal,appointed_by=people['admin'],active_from=now-timezone.timedelta(days=2*i+2),active_until=now-timezone.timedelta(days=2*i+1))
        StaffRole.objects.create(membership=membership,role='president',granted_by=people['admin'])
    client.force_login(people['secretary'])
    with granted_roles('ctm_app',session=True):
        for suffix in ['memberships/','role-history/']:
            first = client.get(f"/api/system/accounts/{people['member'].pk}/{suffix}").json()
            second = client.get(f"/api/system/accounts/{people['member'].pk}/{suffix}?offset=50").json()
            assert first['next_offset'] == 50 and len(first['items']) == 50
            assert second['next_offset'] is None and len(second['items']) == 3
            assert len({row['id'] for row in first['items']+second['items']}) == 53
            assert client.get(f"/api/system/accounts/{people['member'].pk}/{suffix}?limit=0").status_code == 422
