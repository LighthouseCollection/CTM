"""#237 / D-0056: Undo of a first assignment needs an audited unassign.

DELETE /api/cases/<id>/assignment/ clears the case manager, for the same
people who may record an assignment (under an active president's authority).
The assignment history stays; one case_unassigned audit entry is added.
Refused for a closed case, a case without a manager, or one scheduled for a
hearing on an open session. Fictional data, real app role.
"""
from datetime import date

import pytest

from tribunal import models as m
from tribunal.services.applications import submit_application
from tribunal.services.council import assign_case, create_session, place_agenda
from tests.test_core_policy_completion import granted_roles  # noqa: F401  (fixture)

pytestmark = pytest.mark.django_db


@pytest.fixture
def assigned(ready_application, people):
    app = ready_application
    submit_application(app.owner, app.pk, "unassign-237", {"accepted": True, "name": "John Smith"})
    app.refresh_from_db()
    assign_case(people["admin"], app.case_id, people["member"].pk, people["president"].pk)
    return app.case


def unassign(granted_roles, client, actor, case):
    client.force_login(actor)
    with granted_roles("ctm_app", session=True):
        return client.delete(f"/api/cases/{case.pk}/assignment/")


@pytest.mark.parametrize("role", ["admin", "secretary"])
def test_assignment_recorders_can_undo_a_first_assignment(granted_roles, client, people, assigned, role):
    response = unassign(granted_roles, client, people[role], assigned)
    assert response.status_code == 200, response.content
    assert response.json() == {"case_id": str(assigned.pk), "assigned_member_id": None}
    assigned.refresh_from_db()
    assert assigned.assigned_member_id is None
    assert m.CaseAssignment.objects.filter(case=assigned).count() == 1  # history kept
    trace = m.AuditEvent.objects.get(action="case_unassigned", case=assigned)
    assert trace.actor_id == people[role].pk
    assert trace.metadata == {"previous_member_id": str(people["member"].pk)}


@pytest.mark.parametrize("role", ["member", "applicant"])
def test_others_cannot_unassign(granted_roles, client, people, assigned, role):
    assert unassign(granted_roles, client, people[role], assigned).status_code == 403
    assigned.refresh_from_db()
    assert assigned.assigned_member_id == people["member"].pk


def test_unassigned_case_is_refused_with_a_reason(granted_roles, client, people, assigned):
    unassign(granted_roles, client, people["admin"], assigned)
    response = unassign(granted_roles, client, people["admin"], assigned)
    assert response.status_code == 422
    assert "no case manager" in response.json()["messages"][0]


def test_case_scheduled_for_a_hearing_keeps_its_manager(granted_roles, client, people, assigned):
    session = create_session(people["admin"], date(2031, 6, 7), location="Hall 2")
    place_agenda(people["member"], session.pk, assigned.pk)
    response = unassign(granted_roles, client, people["admin"], assigned)
    assert response.status_code == 422
    assert "hearing" in response.json()["messages"][0]
    assigned.refresh_from_db()
    assert assigned.assigned_member_id == people["member"].pk
