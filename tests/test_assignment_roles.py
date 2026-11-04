"""F15: explicit dual-role assignment authority retains one actual person twice."""
import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.utils import timezone
from tribunal import models as m
from tribunal.services.applications import submit_application
from tribunal.services.council import assign_case
from tribunal.services.staff_roles import (
    create_tribunal, grant_assignment_presidency, revoke_assignment_authority, assignment_president,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def institution(people, settings):
    tribunal = create_tribunal(people["admin"], "TEST", "Test institution", "مؤسسة تجريبية")
    settings.CTM_TRIBUNAL_ID = str(tribunal.pk)
    return tribunal


@pytest.fixture
def filed(ready_application):
    submit_application(ready_application.owner, ready_application.pk, "dual-role", {"accepted": True, "name": "John Smith"})
    ready_application.refresh_from_db()
    return ready_application


def test_f15_same_admin_can_authorize_and_record_with_explicit_presidency(filed, people, institution):
    actor = people["admin"]
    with pytest.raises(PermissionDenied):
        assign_case(actor, filed.case_id, people["member"].pk, actor.pk)
    role = grant_assignment_presidency(actor, actor.pk, institution.pk)
    again = grant_assignment_presidency(actor, actor.pk, institution.pk)
    assert again.pk == role.pk and m.StaffMembership.objects.count() == 1
    assert role.granted_by_id == actor.pk and role.membership.appointed_by_id == actor.pk
    record = assign_case(actor, filed.case_id, people["member"].pk, actor.pk)
    assert record.actor_id == record.president_id == actor.pk
    assert record.member_id == people["member"].pk
    actor.refresh_from_db()
    assert actor.role == "admin" and not actor.has_usable_password()
    assert m.AuditEvent.objects.filter(source_id=record.pk, actor=actor).exists()


def test_f15_revocation_expiry_and_other_tribunal_do_not_authorize(filed, people, institution, settings):
    actor = people["admin"]
    role = grant_assignment_presidency(actor, actor.pk, institution.pk)
    revoke_assignment_authority(actor, role.pk)
    assert not assignment_president(actor)
    with pytest.raises(PermissionDenied):
        assign_case(actor, filed.case_id, people["member"].pk, actor.pk)
    replacement = grant_assignment_presidency(actor, actor.pk, institution.pk)
    assert replacement.pk != role.pk and m.StaffRole.objects.count() == 2
    other = create_tribunal(actor, "OTHER", "Other test institution")
    settings.CTM_TRIBUNAL_ID = str(other.pk)
    assert not assignment_president(actor)
    settings.CTM_TRIBUNAL_ID = str(institution.pk)
    m.StaffMembership.objects.filter(pk=replacement.membership_id).update(active_until=timezone.now())
    assert not assignment_president(actor)


def test_assignment_uses_active_president_when_not_supplied(filed, people, institution):
    record = assign_case(people["admin"], filed.case_id, people["member"].pk)
    assert record.member_id == people["member"].pk
    assert record.president_id == people["president"].pk


def test_f15_no_implicit_decree_approval_power(filed, people, institution):
    from tribunal.services.decisions import record_decision, approve_decision
    actor = people["admin"]
    grant_assignment_presidency(actor, actor.pk, institution.pk)
    decision = record_decision(actor, filed.proceeding_id, "deferred", "More inquiry", {})
    with pytest.raises(m.Account.DoesNotExist):
        approve_decision(actor, decision.pk, actor.pk)
    assert not m.PresidentialApproval.objects.exists()


def test_f15_configuration_membership_and_grant_api_permissions(client, filed, people, institution):
    from tests.test_council_contract import login
    login(client, people["admin"])
    response = client.post("/api/council/assignment-authorities/", data={"account_id": str(people["admin"].pk), "tribunal_id": str(institution.pk)}, content_type="application/json")
    assert response.status_code == 201
    role_id = response.json()["id"]
    listing = client.get("/api/council/members/").json()
    # The voting roster stays council-only (3721917); F15 holders are listed separately.
    assert str(people["admin"].pk) not in {row["id"] for row in listing["items"]}
    actor = next(row for row in listing["assignment_authorities"] if row["id"] == str(people["admin"].pk))
    assert actor["can_authorize_assignment"] and actor["can_record_assignment"] and actor["role"] == "admin"
    assert "president" not in actor
    response = client.post(f"/api/cases/{filed.case_id}/assignment/", data={"member_id": str(people["member"].pk), "president_id": str(people["admin"].pk)}, content_type="application/json")
    assert response.status_code == 201
    history = client.get(f"/api/cases/{filed.case_id}/").json()["assignment_history"]
    assert history[-1]["president_id"] == history[-1]["actor_id"] == str(people["admin"].pk)
    login(client, filed.owner)
    assert "assignment_history" not in client.get(f"/api/cases/{filed.case_id}/").json()
    login(client, people["admin"])
    assert client.post(f"/api/council/assignment-authorities/{role_id}/revoke/").status_code == 200
    for role in ["member", "president", "secretary", "applicant"]:
        login(client, people[role])
        assert client.post("/api/council/assignment-authorities/", data={}, content_type="application/json").status_code == 403
        assert client.get("/api/council/tribunals/").status_code == 403
        assert client.post(f"/api/council/assignment-authorities/{role_id}/revoke/").status_code == 403


def test_f15_no_inferred_institution_or_applicant_enrollment(people, settings, institution):
    with pytest.raises(PermissionDenied):
        grant_assignment_presidency(people["admin"], people["applicant"].pk, institution.pk)
    settings.CTM_TRIBUNAL_ID = ""
    with pytest.raises(ValidationError, match="configured"):
        grant_assignment_presidency(people["admin"], people["admin"].pk, institution.pk)
    assert not m.StaffRole.objects.exists() and not m.StaffMembership.objects.exists()


def test_f15_presidency_does_not_grant_administrative_recorder_power(filed, people, institution):
    grant_assignment_presidency(people["admin"], people["member"].pk, institution.pk)
    assert assignment_president(people["member"])
    with pytest.raises(PermissionDenied):
        assign_case(people["member"], filed.case_id, people["member"].pk, people["member"].pk)
    record = assign_case(people["secretary"], filed.case_id, people["member"].pk, people["member"].pk)
    assert record.actor_id == people["secretary"].pk and record.president_id == people["member"].pk


def test_f15_primary_president_can_record_with_explicit_assignment_admin_role(client, filed, people, institution):
    from tribunal.services.staff_roles import grant_assignment_authority
    from tests.test_council_contract import login
    target = people["president"]
    with pytest.raises(PermissionDenied):
        assign_case(target, filed.case_id, people["member"].pk, target.pk)
    grant = grant_assignment_authority(people["admin"], target.pk, institution.pk, "admin")
    record = assign_case(target, filed.case_id, people["member"].pk, target.pk)
    assert record.actor_id == record.president_id == target.pk
    login(client, target)
    assert client.get(f"/api/cases/{filed.case_id}/").json()["can_assign"]
    # This assignment role does not grant system settings or role-grant authority.
    assert client.get("/api/system/settings/").status_code == 403
    assert client.post("/api/council/assignment-authorities/", data={}, content_type="application/json").status_code == 403
    revoke_assignment_authority(people["admin"], grant.pk)
    with pytest.raises(PermissionDenied):
        assign_case(target, filed.case_id, people["member"].pk, target.pk)
