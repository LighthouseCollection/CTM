"""Actual runtime role enrollment/profile writes preserve identity and authority."""
import uuid
from unittest.mock import patch
import pytest
from django.db import DatabaseError, connection
from tribunal import models as m
from tribunal.db.context import database_settings
from tribunal.services.member_administration import create_member, edit_member
from tests.test_core_policy_completion import granted_roles
from tests.test_assignment_roles import institution

pytestmark = pytest.mark.django_db


def enrollment(**updates):
    return {'email': 'new-member@example.test', 'first_name': 'New', 'last_name': 'Member', **updates}


def test_member_http_contract_across_adapters(people, institution, client):
    client.force_login(people['admin'])
    response = client.post('/api/system/members/', enrollment(microsoft_subject='preauthorized-immutable-subject'), content_type='application/json')
    assert response.status_code == 201, response.content
    result = response.json()
    assert 'microsoft_subject' not in result
    account = m.Account.objects.get(pk=result['id'])
    assert account.microsoft_subject == 'preauthorized-immutable-subject' and not account.email_verified
    original_person = m.Person.objects.filter(pk=account.person_id).values().get()
    url = f'/api/system/members/{account.pk}/'
    assert client.post(url, {'first_name': 'Corrected', 'expected_version': 0}, content_type='application/json').json()['profile_version'] == 1
    assert client.get(url).json()['first_name'] == 'Corrected'
    assert m.Person.objects.filter(pk=account.person_id).values().get() == original_person


@pytest.mark.parametrize('role', ['member', 'president', 'secretary', 'admin'])
def test_admin_enrolls_explicit_membership_without_fabricating_login(granted_roles, people, institution, client, role):
    client.force_login(people['admin'])
    with granted_roles('ctm_app', session=True):
        response = client.post('/api/system/members/', enrollment(role=role), content_type='application/json')
        assert response.status_code == 201, response.content
        result = response.json()
        assert client.get(f"/api/system/members/{result['id']}/").json()['profile_version'] == 0
    account = m.Account.objects.get(pk=result['id'])
    assert account.role == role and account.email_verified is False
    assert not account.has_usable_password() and not account.is_superuser and not account.microsoft_subject
    membership = m.StaffMembership.objects.get(pk=result['membership_id'])
    grant = m.StaffRole.objects.get(pk=result['enrollment_role_id'])
    assert membership.account_id == account.pk and membership.tribunal_id == institution.pk
    assert membership.appointed_by_id == grant.granted_by_id == people['admin'].pk
    assert grant.membership_id == membership.pk and grant.role == role
    assert m.AuditEvent.objects.filter(action='staff_membership_created', source_id=membership.pk, actor=people['admin']).count() == 1
    assert m.AuditEvent.objects.filter(action='council_enrollment_role_granted', source_id=grant.pk, actor=people['admin']).count() == 1
    assert not m.Outbox.objects.filter(recipient=account).exists()
    assert not any(key in result for key in ['password', 'microsoft_subject', 'token'])


@pytest.mark.parametrize('role', ['secretary', 'member', 'president', 'applicant'])
def test_only_admin_can_enroll_or_edit(granted_roles, people, institution, client, role):
    client.force_login(people[role])
    original = m.Account.objects.get(pk=people['member'].pk).first_name
    with granted_roles('ctm_app', session=True):
        assert client.get('/api/system/members/').status_code == 403
        assert client.post('/api/system/members/', enrollment(), content_type='application/json').status_code == 403
        for target in [people['member'].pk, uuid.uuid4()]:
            assert client.get(f'/api/system/members/{target}/').status_code == 403
            assert client.post(f'/api/system/members/{target}/', {'first_name': 'Changed', 'expected_version': 0}, content_type='application/json').status_code == 403
    assert not m.Account.objects.filter(email='new-member@example.test').exists()
    assert m.Account.objects.get(pk=people['member'].pk).first_name == original


def test_edit_is_versioned_attributed_and_does_not_rewrite_identity(granted_roles, people, client):
    account = people['member']
    before = m.Account.objects.filter(pk=account.pk).values().get()
    person_before = m.Person.objects.filter(pk=account.person_id).values().get()
    client.force_login(people['admin'])
    url = f'/api/system/members/{account.pk}/'
    payload = {'first_name': 'اسم', 'last_name': 'عضو', 'expected_version': 0}
    with granted_roles('ctm_app', session=True):
        response = client.post(url, payload, content_type='application/json')
        assert response.status_code == 200, response.content
        assert response.json()['profile_version'] == 1
        assert client.post(url, payload, content_type='application/json').status_code == 409
        payload['expected_version'] = 1
        assert client.post(url, payload, content_type='application/json').json()['profile_version'] == 1
        assert client.get(url).json()['first_name'] == 'اسم'
    after = m.Account.objects.filter(pk=account.pk).values().get()
    assert {k: v for k, v in before.items() if k not in {'first_name', 'last_name'}} == {k: v for k, v in after.items() if k not in {'first_name', 'last_name'}}
    assert m.Person.objects.filter(pk=account.person_id).values().get() == person_before
    event = m.AuditEvent.objects.get(action='council_member_profile_changed', source_id=account.pk)
    assert event.actor_id == people['admin'].pk
    assert event.metadata == {'before': {'first_name': before['first_name'], 'last_name': before['last_name']},
                              'after': {'first_name': 'اسم', 'last_name': 'عضو'}, 'profile_version': 1}


@pytest.mark.parametrize('payload', [
    {'first_name': 'Changed'}, {'first_name': 'Changed', 'expected_version': True},
    {'first_name': '', 'expected_version': 0}, {'first_name': 'a'*151, 'expected_version': 0},
    {'first_name': 'bad\nname', 'expected_version': 0}, {'first_name': None, 'expected_version': 0},
    {'first_name': 'Changed', 'role': 'admin', 'expected_version': 0},
    {'email': 'replace@example.test', 'expected_version': 0},
    {'microsoft_subject': 'forged', 'expected_version': 0},
])
def test_edit_rejects_bad_names_and_identity_or_role_mutations(granted_roles, people, client, payload):
    client.force_login(people['admin'])
    with granted_roles('ctm_app', session=True):
        response = client.post(f"/api/system/members/{people['member'].pk}/", payload, content_type='application/json')
    assert response.status_code == 422, response.content
    assert not m.AuditEvent.objects.filter(action='council_member_profile_changed').exists()


def test_missing_tribunal_duplicate_and_applicant_are_not_enrolled_or_converted(granted_roles, people, institution, settings, client):
    client.force_login(people['admin'])
    for configured in ['', str(uuid.uuid4())]:
        settings.CTM_TRIBUNAL_ID = configured
        with granted_roles('ctm_app', session=True):
            assert client.post('/api/system/members/', enrollment(), content_type='application/json').status_code == 422
    settings.CTM_TRIBUNAL_ID = str(institution.pk)
    before = m.Account.objects.filter(pk=people['applicant'].pk).values().get()
    with granted_roles('ctm_app', session=True):
        assert client.post('/api/system/members/', enrollment(email=people['applicant'].email.upper()), content_type='application/json').status_code == 422
        assert client.get(f"/api/system/members/{people['applicant'].pk}/").status_code == 404
        assert client.post(f"/api/system/members/{people['applicant'].pk}/", {'first_name': 'Changed', 'expected_version': 0}, content_type='application/json').status_code == 404
    assert m.Account.objects.filter(pk=people['applicant'].pk).values().get() == before
    assert not m.Account.objects.filter(email='new-member@example.test').exists()


def test_audit_failure_rolls_back_enrollment_and_edit(granted_roles, people, institution):
    counts = [model.objects.count() for model in [m.Account, m.Person, m.StaffMembership, m.StaffRole]]
    with pytest.raises(RuntimeError):
        with granted_roles('ctm_app', people['admin'], session=True):
            with patch('tribunal.services.member_administration.audit', side_effect=RuntimeError('synthetic audit failure')):
                create_member(people['admin'], enrollment())
    assert counts == [model.objects.count() for model in [m.Account, m.Person, m.StaffMembership, m.StaffRole]]
    original = people['member'].first_name
    with pytest.raises(RuntimeError):
        with granted_roles('ctm_app', people['admin'], session=True):
            with patch('tribunal.services.member_administration.audit', side_effect=RuntimeError('synthetic audit failure')):
                edit_member(people['admin'], people['member'].pk, {'first_name': 'Changed', 'expected_version': 0})
    assert m.Account.objects.get(pk=people['member'].pk).first_name == original


@pytest.mark.parametrize('field,value', [('role', 'admin'), ('email', 'forged@example.test'),
    ('email_verified', True), ('is_active', False), ('microsoft_subject', 'forged')])
def test_profile_context_cannot_modify_authority_or_identity(granted_roles, people, field, value):
    if field == 'email_verified':
        m.Account.objects.filter(pk=people['member'].pk).update(email_verified=False)
    with pytest.raises(DatabaseError):
        with granted_roles('ctm_app', people['admin'], session=True):
            with database_settings({'ctm.core_operation': 'member_profile', 'ctm.core_target': str(people['member'].pk)}):
                m.Account.objects.filter(pk=people['member'].pk).update(first_name='Forged', **{field: value})


def test_names_require_bound_admin_context_even_for_raw_sql(granted_roles, people):
    for role, actor, bound in [('ctm_app', people['admin'], False), ('ctm_app', people['secretary'], True),
                               ('ctm_worker', people['admin'], True)]:
        with pytest.raises(DatabaseError):
            with granted_roles(role, actor, session=True):
                with database_settings({'ctm.core_operation': 'member_profile' if bound else '',
                                        'ctm.core_target': str(people['member'].pk)}):
                    with connection.cursor() as cursor:
                        cursor.execute('UPDATE tribunal_account SET first_name=%s WHERE id=%s', ['Forged', people['member'].pk])


def test_member_directory_is_bounded_and_excludes_applicants(granted_roles, people, client):
    client.force_login(people['admin'])
    with granted_roles('ctm_app', session=True):
        first = client.get('/api/system/members/?limit=2')
        assert first.status_code == 200, first.content
        data = first.json()
        assert len(data['items']) == 2 and data['next_offset'] == 2
        second = client.get('/api/system/members/?limit=2&offset=2').json()
    rows = data['items'] + second['items']
    assert {row['role'] for row in rows} == {'admin', 'secretary', 'president', 'member'}
    assert len({row['id'] for row in rows}) == 4
    assert all(row['profile_version'] == 0 for row in rows)
    assert all(row['id'] != str(people['applicant'].pk) for row in rows)
    assert all(set(row) == {'id', 'first_name', 'last_name', 'email', 'role', 'active', 'email_verified', 'profile_version'} for row in rows)
