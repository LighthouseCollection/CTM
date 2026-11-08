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


# Ruling on #237 (ctm3-product-lead): the parties hear about a manager change only
# after the undo window; an Undo or Change inside the window tells them nothing.
from datetime import timedelta  # noqa: E402
from unittest.mock import patch  # noqa: E402
from django.utils import timezone  # noqa: E402


def party_accounts(case):
    return [party.account for party in case.parties.select_related("account") if party.account]


def inbox(granted_roles, client, account):
    client.force_login(account)
    with granted_roles("ctm_app", session=True):
        return [row for row in client.get("/api/notifications/").json()["items"] if row["kind"] == "assignment_changed"]


def test_party_notice_waits_for_the_undo_window(granted_roles, client, people, assigned, settings):
    window = settings.CTM_ASSIGNMENT_UNDO_WINDOW_SECONDS
    party = party_accounts(assigned)[0]
    job = m.Outbox.objects.get(kind="assignment_changed", recipient=party, case=assigned)
    assert job.due_at >= timezone.now() + timedelta(seconds=window - 30)
    assert inbox(granted_roles, client, party) == []  # nothing before the window passes
    with patch("django.utils.timezone.now", return_value=timezone.now() + timedelta(seconds=window + 5)):
        assert len(inbox(granted_roles, client, party)) == 1


def test_undo_inside_the_window_tells_the_parties_nothing(granted_roles, client, people, assigned):
    party = party_accounts(assigned)[0]
    assert unassign(granted_roles, client, people["admin"], assigned).status_code == 200
    jobs = m.Outbox.objects.filter(kind="assignment_changed", recipient=party, case=assigned)
    assert jobs.count() == 1 and jobs.get().discarded_at is not None
    later = timezone.now() + timedelta(hours=1)
    with patch("django.utils.timezone.now", return_value=later):
        assert inbox(granted_roles, client, party) == []
    assert m.Notification.objects.filter(recipient=people["member"], kind="assignment_changed").count() >= 2


def test_change_inside_the_window_replaces_the_first_notice(granted_roles, client, people, assigned):
    other = m.Account.objects.create_user(email="second.member@example.test", role="member",
                                          first_name="Second", last_name="Member")
    party = party_accounts(assigned)[0]
    assign_case(people["admin"], assigned.pk, other.pk, people["president"].pk)
    jobs = m.Outbox.objects.filter(kind="assignment_changed", recipient=party, case=assigned).order_by("created_at")
    assert [job.discarded_at is not None for job in jobs] == [True, False]
    with patch("django.utils.timezone.now", return_value=timezone.now() + timedelta(hours=1)):
        names = [row["payload"]["assigned_member"] for row in inbox(granted_roles, client, party)]
    assert names == ["Second Member"]


def test_unassign_after_the_window_tells_the_parties(granted_roles, client, people, assigned, settings):
    party = party_accounts(assigned)[0]
    later = timezone.now() + timedelta(seconds=settings.CTM_ASSIGNMENT_UNDO_WINDOW_SECONDS + 60)
    with patch("django.utils.timezone.now", return_value=later):
        assert unassign(granted_roles, client, people["admin"], assigned).status_code == 200
    first = m.Outbox.objects.filter(kind="assignment_changed", recipient=party, case=assigned).order_by("created_at")
    assert first.count() == 2 and first[0].discarded_at is None  # the first notice was due and stands
    assert first[1].payload["assigned_member"] is None
    with patch("django.utils.timezone.now", return_value=later + timedelta(hours=1)):
        names = [row["payload"]["assigned_member"] for row in inbox(granted_roles, client, party)]
    assert sorted(names, key=str) == sorted([None, "member Test"], key=str)  # history kept, new notice added
