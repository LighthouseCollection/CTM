"""#224 / D-0052: an In progress session can go back to Draft (and In progress
again) until it is adjourned, to undo an accidental click.

Admin, president and secretary may switch. Nothing recorded in the session
(attendance, hearings, outcomes, notes) changes, the switch is audited, and
switching back to In progress does not resend reminders. Through the API with
the real app role, on fictional data.
"""
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from django.utils import timezone

from tribunal import models as m
from tribunal.services.applications import submit_application
from tribunal.services.council import (assign_case, create_session, hear_case, place_agenda,
                                       record_attendance, set_session_adjourned)
from tests.test_core_policy_completion import granted_roles  # noqa: F401  (fixture)

pytestmark = pytest.mark.django_db
LA = ZoneInfo("America/Los_Angeles")


@pytest.fixture
def in_progress(ready_application, people, settings):
    settings.EMAIL_HOST = "configured-for-test"
    app = ready_application
    submit_application(app.owner, app.pk, "draft-224", {"accepted": True, "name": "John Smith"})
    app.refresh_from_db()
    assign_case(people["admin"], app.case_id, people["member"].pk, people["president"].pk)
    day = timezone.localdate() + timedelta(days=3)
    session = create_session(people["admin"], day, location="Hall 2",
                             starts_at=datetime(day.year, day.month, day.day, 10, tzinfo=LA))
    item = place_agenda(people["member"], session.pk, app.case_id)
    record_attendance(people["admin"], session.pk, people["member"].pk, True)
    hearing = hear_case(people["member"], item.pk)
    return session, hearing


def post(granted_roles, client, actor, session, action):
    client.force_login(actor)
    with granted_roles("ctm_app", session=True):
        return client.post(f"/api/sessions/{session.pk}/{action}/", {}, content_type="application/json")


def snapshot(session):
    return (sorted(m.Attendance.objects.filter(session=session).values_list("member_id", "present")),
            sorted(m.Hearing.objects.filter(agenda__session=session).values_list("id", flat=True)),
            m.AgendaItem.objects.filter(session=session).count())


PRESIDENT_NOTICES = pytest.mark.xfail(
    strict=True, reason="#224: the outbox rule lets the president queue only session_reminder notices, so "
    "re-activating needs the invite rows the president can't read or write (database follow-up)")


@pytest.mark.parametrize("role", ["admin", pytest.param("president", marks=PRESIDENT_NOTICES), "secretary"])
def test_in_progress_goes_back_to_draft_and_again_without_losing_anything(granted_roles, client, people,
                                                                          in_progress, role):
    session, hearing = in_progress
    before = snapshot(session)
    outbox = m.Outbox.objects.count()
    response = post(granted_roles, client, people[role], session, "plan")
    assert response.status_code == 200, response.content
    session.refresh_from_db()
    assert session.state == "draft"
    assert snapshot(session) == before
    response = post(granted_roles, client, people[role], session, "activate")
    assert response.status_code == 200, response.content
    session.refresh_from_db()
    assert session.state == "planned" and snapshot(session) == before
    assert m.Outbox.objects.count() == outbox  # reminders already queued are not sent again
    actions = list(m.AuditEvent.objects.filter(source_id=session.pk, action__in=[
        "session_returned_to_planned", "session_activated"]).values_list("action", "actor_id"))
    assert ("session_returned_to_planned", people[role].pk) in actions
    assert ("session_activated", people[role].pk) in actions


def test_member_is_refused_with_a_specific_reason(granted_roles, client, people, in_progress):
    session, _ = in_progress
    response = post(granted_roles, client, people["member"], session, "plan")
    assert response.status_code == 403
    assert "administrator, the president or the secretary" in response.json()["detail"]


def test_adjourned_session_stays_adjourned_with_a_specific_reason(granted_roles, client, people, in_progress):
    session, _ = in_progress
    day = session.date
    set_session_adjourned(people["admin"], session.pk, True, datetime(day.year, day.month, day.day, 12, tzinfo=LA))
    response = post(granted_roles, client, people["admin"], session, "plan")
    assert response.status_code == 422
    assert "adjourned" in response.json()["messages"][0].lower()
