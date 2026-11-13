"""#116 / D-0036 backend: invites, updates, cancellations, reminders, answers.

AC-1 invites, AC-3 update/cancel, AC-4 reminders and Send reminder now,
AC-5 answers (service + API; row security itself is tests/test_session_response_rls.py),
AC-7 "email is not set up". Delivery runs through dispatch_outbox.
"""
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.utils import timezone

from tests.test_core_policy_completion import granted_roles  # noqa: F401 (fixture)
from tribunal.models import Account, CouncilSession, Outbox, SessionResponse
from tribunal.services.council import create_session, reschedule_session, update_session
from tribunal.services.session_reminders import (
    EMAIL_UNAVAILABLE, answer_session, send_reminders_now, session_answers,
)
from tribunal.tasks import dispatch_outbox

pytestmark = pytest.mark.django_db
LA = ZoneInfo("America/Los_Angeles")
COUNCIL = ["member", "president", "secretary", "admin"]


def future_day(days=10):
    return (timezone.now() + timedelta(days=days)).astimezone(LA).date()


def at(day, hour=10, minute=30):
    return datetime(day.year, day.month, day.day, hour, minute, tzinfo=LA)


@pytest.fixture
def email(settings):
    settings.EMAIL_HOST = "configured-for-test"
    return settings


@pytest.fixture
def planned(people, email):
    day = future_day()
    return create_session(people["admin"], day, starts_at=at(day), location="Hall 2")


def rows(kind, session):
    return Outbox.objects.filter(kind=kind, payload__session=str(session.pk)).order_by("recipient__role")


# AC-1 -----------------------------------------------------------------------

def test_planned_session_with_a_start_time_invites_every_active_council_account(people, email):
    inactive = Account.objects.create_user(email="gone@example.test", role="member", first_name="Gone",
                                           last_name="Member", email_verified=True, is_active=False)
    unverified = Account.objects.create_user(email="unverified@example.test", role="member",
                                             first_name="Un", last_name="Verified", email_verified=False)
    day = future_day()
    session = create_session(people["admin"], day, starts_at=at(day), location="Hall 2")

    invites = rows("session_invite", session)
    assert sorted(row.recipient.role for row in invites) == sorted(COUNCIL)
    recipients = {row.recipient_id for row in invites}
    assert people["applicant"].pk not in recipients
    assert inactive.pk not in recipients and unverified.pk not in recipients
    assert all(row.case_id is None for row in invites)
    payload = invites[0].payload
    assert "METHOD:PUBLISH" in payload["ics"] and "SEQUENCE:0" in payload["ics"]
    assert payload["subject"] == f"CTM Council Session {day.isoformat()}"


def test_automatic_reminder_is_queued_for_two_days_before_the_start(people, planned):
    reminders = rows("session_reminder", planned)
    assert reminders.count() == len(COUNCIL)
    assert {row.due_at for row in reminders} == {planned.starts_at - timedelta(days=2)}


def test_draft_or_timeless_session_sends_nothing(people, email):
    day = future_day()
    draft = create_session(people["admin"], day, starts_at=at(day), location="Hall", state="draft")
    timeless = create_session(people["admin"], future_day(12), location="Hall")
    assert not Outbox.objects.filter(payload__session__in=[str(draft.pk), str(timeless.pk)]).exists()


# AC-7 -----------------------------------------------------------------------

def test_without_email_nothing_is_queued_and_the_state_says_so(people, settings):
    settings.EMAIL_HOST = ""
    day = future_day()
    session = create_session(people["admin"], day, starts_at=at(day), location="Hall")
    assert not Outbox.objects.filter(payload__session=str(session.pk)).exists()
    with pytest.raises(ValidationError, match=EMAIL_UNAVAILABLE):
        send_reminders_now(people["secretary"], session.pk)
    assert session_answers(people["secretary"], session.pk)["email_ready"] is False


# AC-3 -----------------------------------------------------------------------

def test_changing_time_or_location_sends_an_update_with_a_higher_sequence(people, planned):
    update_session(people["secretary"], planned.pk, planned.date, starts_at=at(planned.date, 12, 0),
                   location="Hall 3")
    planned.refresh_from_db()
    assert planned.ics_sequence == 1
    updates = rows("session_update", planned)
    assert updates.count() == len(COUNCIL)
    ics = updates[0].payload["ics"]
    assert "SEQUENCE:1" in ics and f"UID:council-session-{planned.pk}@" in ics
    assert updates[0].payload["sequence"] == 1


def test_saving_without_a_change_sends_nothing_new(people, planned):
    update_session(people["secretary"], planned.pk, planned.date, starts_at=planned.starts_at, location="Hall 2")
    planned.refresh_from_db()
    assert planned.ics_sequence == 0
    assert not rows("session_update", planned).exists()


def test_moving_a_session_cancels_the_old_entry_and_invites_to_the_new_one(people, planned):
    source_id = planned.pk
    new_day = planned.date + timedelta(days=7)
    target = reschedule_session(people["secretary"], planned.pk, new_day, {}, "Bishop travelling")
    cancels = Outbox.objects.filter(kind="session_cancel", payload__session=str(source_id))
    assert cancels.count() == len(COUNCIL)
    ics = cancels.first().payload["ics"]
    assert "METHOD:CANCEL" in ics and f"UID:council-session-{source_id}@" in ics and "SEQUENCE:1" in ics
    assert rows("session_invite", target).count() == len(COUNCIL)


# AC-5 -----------------------------------------------------------------------

def test_member_answers_for_themself_and_the_latest_counts(people, planned):
    member = people["member"]
    answer_session(member, planned.pk, "attend")
    answer_session(member, planned.pk, "not_attend")
    assert SessionResponse.objects.filter(session=planned, member=member).count() == 2
    mine = session_answers(member, planned.pk)
    assert mine["mine"]["answer"] == "not_attend"
    assert "members" not in mine  # a member never sees anyone else's answer


def test_secretary_sees_each_member_and_the_confirmed_count(people, planned):
    answer_session(people["member"], planned.pk, "attend")
    answer_session(people["president"], planned.pk, "not_attend")
    view = session_answers(people["secretary"], planned.pk)
    assert (view["confirmed"], view["total"]) == (1, len(COUNCIL))
    by_member = {row["member_id"]: row["answer"] for row in view["members"]}
    assert by_member[str(people["member"].pk)] == "attend"
    assert by_member[str(people["admin"].pk)] is None


@pytest.mark.parametrize("value", ["maybe", "", None])
def test_only_attend_or_not_attend(people, planned, value):
    with pytest.raises(ValidationError):
        answer_session(people["member"], planned.pk, value)


def test_applicant_cannot_answer_or_read(people, planned):
    with pytest.raises(PermissionDenied):
        answer_session(people["applicant"], planned.pk, "attend")
    with pytest.raises(PermissionDenied):
        session_answers(people["applicant"], planned.pk)


def test_answers_close_when_the_session_starts(people, email):
    session = CouncilSession.objects.create(date=date(2020, 1, 2), starts_at=at(date(2020, 1, 2)), location="Hall")
    with pytest.raises(ValidationError):
        answer_session(people["member"], session.pk, "attend")


# AC-4 -----------------------------------------------------------------------

def test_send_now_is_for_secretary_president_or_admin_only(people, planned):
    with pytest.raises(PermissionDenied):
        send_reminders_now(people["member"], planned.pk)
    with pytest.raises(PermissionDenied):
        send_reminders_now(people["applicant"], planned.pk)


def test_send_now_reaches_only_members_without_an_answer_and_once_an_hour(people, planned):
    answer_session(people["member"], planned.pk, "attend")
    now = timezone.now()
    assert send_reminders_now(people["president"], planned.pk, now=now) == len(COUNCIL) - 1
    manual = Outbox.objects.filter(kind="session_reminder", payload__session=str(planned.pk), payload__manual=True)
    assert people["member"].pk not in set(manual.values_list("recipient_id", flat=True))
    with pytest.raises(ValidationError, match="last hour"):
        send_reminders_now(people["secretary"], planned.pk, now=now + timedelta(minutes=30))
    assert send_reminders_now(people["secretary"], planned.pk, now=now + timedelta(hours=2)) == len(COUNCIL) - 1


# Delivery -------------------------------------------------------------------

def test_invite_is_delivered_with_the_calendar_file(people, planned, mailoutbox):
    Outbox.objects.filter(kind="session_reminder").delete()
    assert dispatch_outbox() == len(COUNCIL)
    message = mailoutbox[0]
    assert message.subject == f"CTM Council Session {planned.date.isoformat()}"
    assert "https://ctm.lighthouseway.org" in message.body
    name, content, mimetype = message.attachments[0]
    assert name == "ctm-council-session.ics"
    assert mimetype.startswith("text/calendar") and "method=PUBLISH" in mimetype
    assert "BEGIN:VCALENDAR" in content
    assert rows("session_invite", planned).filter(delivered_at__isnull=False).count() == len(COUNCIL)


def test_superseded_invite_and_answered_reminder_are_not_sent(people, planned, mailoutbox):
    answer_session(people["member"], planned.pk, "attend")
    update_session(people["secretary"], planned.pk, planned.date, starts_at=planned.starts_at, location="Hall 9")
    Outbox.objects.filter(kind="session_reminder").update(due_at=timezone.now())
    dispatch_outbox(limit=100)
    sent = [(m.subject, m.to[0]) for m in mailoutbox]
    assert not any(subject.startswith("CTM Council Session") for subject, _ in sent)  # old invites superseded
    assert sum(subject.startswith("Updated:") for subject, _ in sent) == len(COUNCIL)
    reminded = {to for subject, to in sent if subject.startswith("Reminder:")}
    assert people["member"].email not in reminded
    assert len(reminded) == len(COUNCIL) - 1


# API ------------------------------------------------------------------------

def login(client, account):
    client.force_login(account)


def test_api_member_answers_for_themself(granted_roles, people, planned, client):
    login(client, people["member"])
    with granted_roles("ctm_app", session=True):
        response = client.post(f"/api/sessions/{planned.pk}/answer/", {"answer": "attend"},
                               content_type="application/json")
        assert response.status_code == 200, response.content
        assert response.json()["mine"]["answer"] == "attend"
        mine = client.get(f"/api/sessions/{planned.pk}/answers/").json()
        assert "members" not in mine and mine["mine"]["answer"] == "attend"


def test_api_member_cannot_send_reminders(granted_roles, people, planned, client):
    login(client, people["member"])
    with granted_roles("ctm_app", session=True):
        assert client.post(f"/api/sessions/{planned.pk}/reminders/").status_code == 403


def test_api_secretary_send_now_and_email_state(granted_roles, people, planned, client, settings):
    login(client, people["secretary"])
    with granted_roles("ctm_app", session=True):
        response = client.post(f"/api/sessions/{planned.pk}/reminders/")
        assert response.status_code == 200, response.content
        assert response.json() == {"queued": len(COUNCIL)}
        settings.EMAIL_HOST = ""
        response = client.post(f"/api/sessions/{planned.pk}/reminders/")
        assert response.status_code == 422
        assert EMAIL_UNAVAILABLE in response.json()["messages"]


# #365 (#359 backend): deleting an announced Draft session ------------------------

def announced_draft(people, planned):
    """In progress (invites queued), answered, then returned to Draft (D-0052)."""
    from tribunal.services.council import return_session_to_planned
    answer_session(people["member"], planned.pk, "attend")
    answer_session(people["president"], planned.pk, "not_attend")
    return_session_to_planned(people["admin"], planned.pk)
    planned.refresh_from_db()
    assert planned.state == "draft"
    return planned


def test_deleting_an_announced_draft_queues_a_cancel_and_removes_the_answers(people, planned):
    from tribunal.services.council import delete_draft_session
    draft = announced_draft(people, planned)
    session_id = draft.pk
    delete_draft_session(people["admin"], session_id)
    assert not CouncilSession.objects.filter(pk=session_id).exists()
    assert not SessionResponse.objects.filter(session_id=session_id).exists()
    cancels = Outbox.objects.filter(kind="session_cancel", payload__session=str(session_id))
    assert cancels.count() == len(COUNCIL)
    ics = cancels.first().payload["ics"]
    assert "METHOD:CANCEL" in ics and f"UID:council-session-{session_id}@" in ics and "SEQUENCE:1" in ics


def test_deleting_an_announced_draft_through_the_api_is_not_a_server_error(granted_roles, people, planned, client):
    draft = announced_draft(people, planned)
    login(client, people["secretary"])
    with granted_roles("ctm_app", session=True):
        response = client.delete(f"/api/sessions/{draft.pk}/")
    assert response.status_code == 204, response.content
    assert not CouncilSession.objects.filter(pk=draft.pk).exists()
    assert Outbox.objects.filter(kind="session_cancel", payload__session=str(draft.pk)).count() == len(COUNCIL)


def test_deleting_a_draft_that_was_never_announced_queues_no_cancel(people, email):
    from tribunal.services.council import delete_draft_session
    day = future_day()
    draft = create_session(people["admin"], day, starts_at=at(day), location="Hall 2", state="draft")
    delete_draft_session(people["admin"], draft.pk)
    assert not Outbox.objects.filter(payload__session=str(draft.pk)).exists()


def test_deleting_an_announced_draft_without_email_set_up_fakes_no_send(people, planned, settings):
    from tribunal.services.council import delete_draft_session
    draft = announced_draft(people, planned)
    settings.EMAIL_HOST = ""
    delete_draft_session(people["admin"], draft.pk)
    assert not CouncilSession.objects.filter(pk=draft.pk).exists()
    assert not Outbox.objects.filter(kind="session_cancel", payload__session=str(draft.pk)).exists()
