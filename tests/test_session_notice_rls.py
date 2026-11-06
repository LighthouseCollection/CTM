"""#116 / D-0036 database part 2: council session emails in the Outbox.

- who may queue session_invite / session_update / session_cancel / session_reminder
- the president may read session reminder rows (once-an-hour limit)
- the worker's ctm_session_delivery_current(outbox id) check
"""
import uuid
from datetime import date, timedelta

import pytest
from django.db import DatabaseError, connection, transaction
from django.utils import timezone

from tribunal.models import Account, CouncilSession, Outbox
from tests.test_core_policy_completion import granted_roles  # noqa: F401  (fixture)

pytestmark = pytest.mark.django_db


@pytest.fixture
def session(db):
    return CouncilSession.objects.create(date=date(2030, 6, 7), starts_at=timezone.now() + timedelta(days=5),
                                         location="Hall", ics_sequence=2)


def queue(granted_roles, actor, session, recipient, kind="session_invite", *, sequence=None, key=None,
          manual=False, case=None):
    sequence = session.ics_sequence if sequence is None else sequence
    payload = {"session": str(session.pk), "sequence": sequence, "subject": "CTM Council Session", "body": "", "ics": ""}
    if manual:
        payload["manual"] = True
    key = key or f"{kind}:{session.pk}:{sequence}:{recipient.pk}"
    with granted_roles("ctm_app", actor):
        return Outbox.objects.create(key=key, kind=kind, recipient=recipient, payload=payload, case=case).pk


def refused(*args, **kwargs):
    with pytest.raises(DatabaseError):
        queue(*args, **kwargs)


@pytest.mark.parametrize("kind", ["session_invite", "session_update", "session_cancel", "session_reminder"])
@pytest.mark.parametrize("sender", ["admin", "secretary"])
def test_admin_and_secretary_queue_session_emails_without_a_notification(granted_roles, people, session, kind, sender):
    pk = queue(granted_roles, people[sender], session, people["member"], kind)
    row = Outbox.objects.get(pk=pk)
    assert row.queued_by_id == people[sender].pk and row.case_id is None


def test_president_queues_reminders_only(granted_roles, people, session):
    president = people["president"]
    queue(granted_roles, president, session, people["member"], "session_reminder")
    for kind in ["session_invite", "session_update", "session_cancel"]:
        refused(granted_roles, president, session, people["member"], kind)


@pytest.mark.parametrize("sender", ["member", "applicant"])
def test_member_and_applicant_cannot_queue_session_emails(granted_roles, people, session, sender):
    refused(granted_roles, people[sender], session, people["member"])


@pytest.mark.parametrize("problem", ["applicant", "inactive", "unverified"])
def test_recipient_must_be_an_active_verified_council_account(granted_roles, people, session, problem):
    recipient = people["applicant"] if problem == "applicant" else people["member"]
    if problem == "inactive":
        Account.objects.filter(pk=recipient.pk).update(is_active=False)
    if problem == "unverified":
        Account.objects.filter(pk=recipient.pk).update(email_verified=False)
    refused(granted_roles, people["secretary"], session, recipient)


def test_sequence_must_match_the_session_and_the_key(granted_roles, people, session):
    secretary, member = people["secretary"], people["member"]
    refused(granted_roles, secretary, session, member, sequence=1)
    refused(granted_roles, secretary, session, member, key=f"session_invite:{session.pk}:9:{member.pk}")
    refused(granted_roles, secretary, session, member, key=f"session_invite:{uuid.uuid4()}:2:{member.pk}")


def test_case_bound_session_email_is_refused(granted_roles, people, session, ready_application):
    refused(granted_roles, people["secretary"], session, people["member"], case=ready_application.case)


def test_unknown_session_is_refused(granted_roles, people, session):
    ghost = CouncilSession(pk=uuid.uuid4(), ics_sequence=2)
    refused(granted_roles, people["secretary"], ghost, people["member"])


def test_manual_reminder_uses_an_hour_bucket_key(granted_roles, people, session):
    member = people["member"]
    bucket = timezone.now().strftime("%Y%m%d%H")
    queue(granted_roles, people["president"], session, member, "session_reminder", manual=True,
          key=f"session_reminder:{session.pk}:now:{bucket}:{member.pk}")
    # A bucket key without the manual flag, or the flag on an invite, is refused.
    refused(granted_roles, people["secretary"], session, people["secretary"], "session_reminder",
            key=f"session_reminder:{session.pk}:now:{bucket}:{people['secretary'].pk}")
    refused(granted_roles, people["secretary"], session, people["secretary"], "session_invite", manual=True)


def test_president_reads_session_reminders_but_not_other_outbox_rows(granted_roles, people, session):
    reminder = queue(granted_roles, people["secretary"], session, people["member"], "session_reminder")
    invite = queue(granted_roles, people["secretary"], session, people["member"], "session_invite")
    with granted_roles("ctm_app", people["president"]):
        visible = set(Outbox.objects.filter(pk__in=[reminder, invite]).values_list("pk", flat=True))
    assert visible == {reminder}
    with granted_roles("ctm_app", people["member"]):
        assert not Outbox.objects.filter(pk__in=[reminder, invite]).exists()


def current(granted_roles, outbox_id):
    with granted_roles("ctm_worker"), connection.cursor() as cursor:
        cursor.execute("SELECT public.ctm_session_delivery_current(%s)", [str(outbox_id)])
        return cursor.fetchone()[0]


def test_invite_is_current_until_the_session_changes_or_starts(granted_roles, people, session):
    pk = queue(granted_roles, people["secretary"], session, people["member"])
    assert current(granted_roles, pk) is True
    CouncilSession.objects.filter(pk=session.pk).update(ics_sequence=3)
    assert current(granted_roles, pk) is False
    CouncilSession.objects.filter(pk=session.pk).update(ics_sequence=4)
    pk = queue(granted_roles, people["secretary"], CouncilSession.objects.get(pk=session.pk), people["member"])
    CouncilSession.objects.filter(pk=session.pk).update(starts_at=timezone.now() - timedelta(minutes=1))
    assert current(granted_roles, pk) is False


def test_reminder_stops_once_the_member_answers(granted_roles, people, session):
    member = people["member"]
    pk = queue(granted_roles, people["secretary"], session, member, "session_reminder")
    assert current(granted_roles, pk) is True
    with granted_roles("ctm_app", member), connection.cursor() as cursor:
        cursor.execute("INSERT INTO public.tribunal_sessionresponse(id,created_at,session_id,member_id,answer) "
                       "VALUES (gen_random_uuid(), now(), %s, %s, 'attend')", [str(session.pk), str(member.pk)])
    assert current(granted_roles, pk) is False


def test_cancel_is_current_while_its_sequence_holds_or_the_session_is_gone(granted_roles, people, session):
    pk = queue(granted_roles, people["secretary"], session, people["member"], "session_cancel")
    assert current(granted_roles, pk) is True
    CouncilSession.objects.filter(pk=session.pk).update(ics_sequence=3)
    assert current(granted_roles, pk) is False
    # A cancel for a session that no longer exists (moved and deleted) still goes out.
    Outbox.objects.filter(pk=pk).update(payload={"session": str(uuid.uuid4()), "sequence": 2})
    assert current(granted_roles, pk) is True


def test_delivery_check_is_worker_only(granted_roles, people, session):
    pk = queue(granted_roles, people["secretary"], session, people["member"])
    with pytest.raises(DatabaseError):
        with granted_roles("ctm_app", people["admin"]), connection.cursor() as cursor:
            cursor.execute("SELECT public.ctm_session_delivery_current(%s)", [str(pk)])
