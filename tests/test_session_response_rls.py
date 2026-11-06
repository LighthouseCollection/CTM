"""#116 / D-0036 database part: council session attendance answers (AC-5) and
the .ics SEQUENCE counter (AC-2/AC-3).

Runs as the restricted runtime role so row security is real.
"""
from datetime import date, timedelta

import pytest
from django.db import DatabaseError, connection, transaction
from django.utils import timezone

from tribunal.models import Account, CouncilSession
from tests.test_core_policy_completion import granted_roles  # noqa: F401  (fixture)

pytestmark = pytest.mark.django_db

COUNCIL = ["member", "president", "secretary", "admin"]


@pytest.fixture
def session(db):
    return CouncilSession.objects.create(date=date(2030, 3, 4), starts_at=timezone.now() + timedelta(days=3), location="Hall")


def answer(granted_roles, actor, session, value="attend", member=None, created_at=None):
    with granted_roles("ctm_app", actor) as _, connection.cursor() as cursor:
        cursor.execute(
            "INSERT INTO public.tribunal_sessionresponse(id,created_at,session_id,member_id,answer) "
            "VALUES (gen_random_uuid(), coalesce(%s, now()), %s, %s, %s) RETURNING created_at",
            [created_at, str(session.pk), str((member or actor).pk), value])
        return cursor.fetchone()[0]


def visible(granted_roles, actor, session):
    with granted_roles("ctm_app", actor) as _, connection.cursor() as cursor:
        cursor.execute("SELECT member_id::text, answer FROM public.tribunal_sessionresponse WHERE session_id=%s "
                       "ORDER BY created_at, id", [str(session.pk)])
        return cursor.fetchall()


def refused(granted_roles, actor, session, **kwargs):
    with pytest.raises(DatabaseError):
        answer(granted_roles, actor, session, **kwargs)


def test_member_answers_for_themself_and_the_latest_answer_counts(granted_roles, people, session):
    member = people["member"]
    answer(granted_roles, member, session, "attend")
    answer(granted_roles, member, session, "not_attend")
    rows = visible(granted_roles, member, session)
    assert rows == [(str(member.pk), "attend"), (str(member.pk), "not_attend")]


def test_member_cannot_answer_for_or_read_another_member(granted_roles, people, session):
    member, other = people["member"], people["president"]
    answer(granted_roles, other, session, "attend")
    refused(granted_roles, member, session, member=other)
    assert visible(granted_roles, member, session) == []


@pytest.mark.parametrize("reader", ["secretary", "president", "admin"])
def test_secretary_president_and_admin_read_every_answer(granted_roles, people, session, reader):
    answer(granted_roles, people["member"], session, "attend")
    answer(granted_roles, people["secretary"], session, "not_attend")
    assert len(visible(granted_roles, people[reader], session)) == 2


def test_applicant_gets_nothing(granted_roles, people, session):
    answer(granted_roles, people["member"], session, "attend")
    assert visible(granted_roles, people["applicant"], session) == []
    refused(granted_roles, people["applicant"], session)


def test_inactive_council_account_cannot_answer(granted_roles, people, session):
    member = people["member"]
    Account.objects.filter(pk=member.pk).update(is_active=False)
    refused(granted_roles, member, session)


@pytest.mark.parametrize("state", ["started", "no_start_time", "closed"])
def test_answers_are_refused_once_the_session_has_started(granted_roles, people, session, state):
    if state == "started":
        CouncilSession.objects.filter(pk=session.pk).update(starts_at=timezone.now() - timedelta(minutes=1))
    elif state == "no_start_time":
        CouncilSession.objects.filter(pk=session.pk).update(starts_at=None)
    else:
        CouncilSession.objects.filter(pk=session.pk).update(state="closed", closed_at=timezone.now())
    refused(granted_roles, people["member"], session)


def test_only_attend_or_not_attend_is_accepted(granted_roles, people, session):
    refused(granted_roles, people["member"], session, value="maybe")


def test_answer_time_is_the_database_clock(granted_roles, people, session):
    # A forged earlier created_at cannot reorder answers.
    stored = answer(granted_roles, people["member"], session, created_at=timezone.now() - timedelta(days=30))
    assert abs((stored - timezone.now()).total_seconds()) < 60


@pytest.mark.parametrize("statement", [
    "UPDATE public.tribunal_sessionresponse SET answer='not_attend' WHERE member_id=%s",
    "DELETE FROM public.tribunal_sessionresponse WHERE member_id=%s",
])
def test_answers_are_append_only(granted_roles, people, session, statement):
    member = people["member"]
    answer(granted_roles, member, session, "attend")
    for actor in [member, people["admin"]]:
        # Row security gives the runtime role no row to change or remove.
        with granted_roles("ctm_app", actor) as _, connection.cursor() as cursor:
            cursor.execute(statement, [str(member.pk)])
            assert cursor.rowcount == 0
    with pytest.raises(DatabaseError), transaction.atomic(), connection.cursor() as cursor:
        cursor.execute(statement, [str(member.pk)])  # even the owner is refused by the history guard
    assert visible(granted_roles, people["admin"], session) == [(str(member.pk), "attend")]


def test_moving_a_session_removes_its_answers_through_the_planned_reschedule(granted_roles, people):
    from tribunal.services import council
    admin = people["admin"]
    with granted_roles("ctm_app", admin):
        source = council.create_session(admin, date(2031, 5, 6))
    CouncilSession.objects.filter(pk=source.pk).update(starts_at=timezone.now() + timedelta(days=5))
    answer(granted_roles, people["member"], source, "attend")
    with granted_roles("ctm_app", admin):
        target = council.reschedule_session(admin, source.pk, date(2031, 5, 7), {}, "Move meeting")
    assert not CouncilSession.objects.filter(pk=source.pk).exists()
    assert visible(granted_roles, admin, target) == []
    with connection.cursor() as cursor:
        cursor.execute("SELECT count(*) FROM public.tribunal_sessionresponse WHERE session_id=%s", [str(source.pk)])
        assert cursor.fetchone()[0] == 0


def test_table_forces_row_security():
    with connection.cursor() as cursor:
        cursor.execute("SELECT relrowsecurity, relforcerowsecurity FROM pg_class "
                       "WHERE oid='public.tribunal_sessionresponse'::regclass")
        assert cursor.fetchone() == (True, True)


def test_ics_sequence_starts_at_zero_and_never_goes_down(session):
    session.refresh_from_db()
    assert session.ics_sequence == 0
    CouncilSession.objects.filter(pk=session.pk).update(ics_sequence=1)
    with pytest.raises(DatabaseError), transaction.atomic():
        CouncilSession.objects.filter(pk=session.pk).update(ics_sequence=0)
    session.refresh_from_db()
    assert session.ics_sequence == 1
