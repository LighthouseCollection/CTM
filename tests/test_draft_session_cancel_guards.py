"""#359 (#116 part 1, database): deleting a Draft session that was announced.

A session goes In progress (invites queued), members answer, it returns to Draft
(D-0052) and is then deleted. Inside the delete context (the setting
ctm.delete_draft_session = that session's id, 0055) the database now lets the
service:
- queue a session_cancel for the Draft session (0070 accepted notices only while planned),
- raise the calendar sequence of the Draft session,
- delete the session's answers together with the session (0069 refused it).
Everything else in 0055, 0069 and 0070 stays.
"""
import uuid
from datetime import date, timedelta

import pytest
from django.db import DatabaseError, connection
from django.utils import timezone

from tests.test_core_policy_completion import granted_roles  # noqa: F401  (fixture)
from tribunal.db.context import database_settings
from tribunal.models import CouncilSession, Outbox, SessionResponse

pytestmark = pytest.mark.django_db


@pytest.fixture
def draft(db):
    return CouncilSession.objects.create(date=date(2030, 6, 7), starts_at=timezone.now() + timedelta(days=5),
                                         location="Hall", state="draft", ics_sequence=2)


def context(session):
    return database_settings({"ctm.delete_draft_session": str(session.pk)})


def cancel(granted_roles, actor, session, recipient, *, sequence=None, kind="session_cancel", set_context=True):
    sequence = session.ics_sequence if sequence is None else sequence
    payload = {"session": str(session.pk), "sequence": sequence, "subject": "CTM Council Session", "body": "", "ics": ""}
    with granted_roles("ctm_app", actor):
        if set_context:
            with context(session):
                return Outbox.objects.create(key=f"{kind}:{session.pk}:{sequence}:{recipient.pk}", kind=kind,
                                             recipient=recipient, payload=payload).pk
        return Outbox.objects.create(key=f"{kind}:{session.pk}:{sequence}:{recipient.pk}", kind=kind,
                                     recipient=recipient, payload=payload).pk


@pytest.mark.parametrize("sender", ["admin", "secretary"])
def test_cancel_for_a_draft_session_is_queued_inside_the_delete_context(granted_roles, people, draft, sender):
    pk = cancel(granted_roles, people[sender], draft, people["member"])
    assert Outbox.objects.get(pk=pk).queued_by_id == people[sender].pk


def test_cancel_for_a_draft_session_is_refused_outside_the_delete_context(granted_roles, people, draft):
    with pytest.raises(DatabaseError):
        cancel(granted_roles, people["admin"], draft, people["member"], set_context=False)


def test_cancel_is_refused_when_the_context_names_another_session(granted_roles, people, draft):
    other = CouncilSession.objects.create(date=date(2030, 7, 5), state="draft")
    payload = {"session": str(draft.pk), "sequence": 2, "subject": "s", "body": "", "ics": ""}
    with pytest.raises(DatabaseError):
        with granted_roles("ctm_app", people["admin"]), context(other):
            Outbox.objects.create(key=f"session_cancel:{draft.pk}:2:{people['member'].pk}", kind="session_cancel",
                                  recipient=people["member"], payload=payload)


@pytest.mark.parametrize("kind", ["session_invite", "session_update", "session_reminder"])
def test_only_a_cancel_is_queued_for_a_draft_session(granted_roles, people, draft, kind):
    with pytest.raises(DatabaseError):
        cancel(granted_roles, people["admin"], draft, people["member"], kind=kind)


def test_the_other_0070_conditions_still_apply_to_a_draft_cancel(granted_roles, people, draft):
    with pytest.raises(DatabaseError):  # wrong sequence
        cancel(granted_roles, people["admin"], draft, people["member"], sequence=1)
    with pytest.raises(DatabaseError):  # applicant is not a council recipient
        cancel(granted_roles, people["admin"], draft, people["applicant"])
    with pytest.raises(DatabaseError):  # a member and the president may not queue it
        cancel(granted_roles, people["member"], draft, people["secretary"])
    with pytest.raises(DatabaseError):
        cancel(granted_roles, people["president"], draft, people["secretary"])


def test_a_planned_session_is_unchanged(granted_roles, people, draft):
    CouncilSession.objects.filter(pk=draft.pk).update(state="planned")
    draft.refresh_from_db()
    pk = cancel(granted_roles, people["admin"], draft, people["member"], set_context=False)
    assert Outbox.objects.filter(pk=pk).exists()


def test_the_sequence_of_the_draft_session_rises_but_never_falls(granted_roles, people, draft):
    with granted_roles("ctm_app", people["admin"]), context(draft):
        assert CouncilSession.objects.filter(pk=draft.pk).update(ics_sequence=3) == 1
    draft.refresh_from_db()
    assert draft.ics_sequence == 3
    with pytest.raises(DatabaseError):
        with granted_roles("ctm_app", people["admin"]), context(draft):
            CouncilSession.objects.filter(pk=draft.pk).update(ics_sequence=1)


def answer(session, member, text="attend"):
    return SessionResponse.objects.create(session=session, member=member, answer=text)


def test_answers_go_with_the_draft_session_inside_the_delete_context(granted_roles, people, draft):
    answer(draft, people["member"])
    answer(draft, people["secretary"], "not_attend")
    with granted_roles("ctm_app", people["admin"]), context(draft):
        CouncilSession.objects.get(pk=draft.pk).delete()
    assert not CouncilSession.objects.filter(pk=draft.pk).exists()
    assert not SessionResponse.objects.filter(session_id=draft.pk).exists()


def test_answers_cannot_be_deleted_outside_the_delete_context(granted_roles, people, draft):
    row = answer(draft, people["member"])
    with granted_roles("ctm_app", people["admin"]):  # row security hides the row: nothing is deleted
        assert SessionResponse.objects.filter(pk=row.pk).delete()[0] == 0
    with granted_roles("ctm_app", people["admin"]):
        assert CouncilSession.objects.filter(pk=draft.pk).delete()[0] == 0
    assert CouncilSession.objects.filter(pk=draft.pk).exists()
    assert SessionResponse.objects.filter(pk=row.pk).exists()


def test_the_context_deletes_only_the_answers_of_its_own_session(granted_roles, people, draft):
    other = CouncilSession.objects.create(date=date(2030, 7, 5), starts_at=timezone.now() + timedelta(days=9),
                                          location="Hall", state="draft")
    keep = answer(other, people["member"])
    with granted_roles("ctm_app", people["admin"]), context(draft):
        assert SessionResponse.objects.filter(pk=keep.pk).delete()[0] == 0
    assert SessionResponse.objects.filter(pk=keep.pk).exists()


def test_a_planned_session_keeps_its_answers_even_with_the_setting(granted_roles, people, draft):
    row = answer(draft, people["member"])
    CouncilSession.objects.filter(pk=draft.pk).update(state="planned")
    with granted_roles("ctm_app", people["admin"]), context(draft):
        assert SessionResponse.objects.filter(pk=row.pk).delete()[0] == 0
    assert SessionResponse.objects.filter(pk=row.pk).exists()


def test_answers_are_still_never_changed(granted_roles, people, draft):
    row = answer(draft, people["member"])
    with granted_roles("ctm_app", people["admin"]), context(draft):
        try:
            changed = SessionResponse.objects.filter(pk=row.pk).update(answer="not_attend")
        except DatabaseError:
            changed = 0
    assert changed == 0
    row.refresh_from_db()
    assert row.answer == "attend"


def test_announce_answer_return_to_draft_cancel_and_delete(granted_roles, people, draft):
    """The reported failure end to end: cancel is queued, the delete no longer fails,
    and the worker still sends the cancel for the vanished session."""
    answer(draft, people["member"])
    with granted_roles("ctm_app", people["admin"]), context(draft):
        CouncilSession.objects.filter(pk=draft.pk).update(ics_sequence=draft.ics_sequence + 1)
    draft.refresh_from_db()
    pk = cancel(granted_roles, people["admin"], draft, people["member"])
    with granted_roles("ctm_app", people["admin"]), context(draft):
        CouncilSession.objects.get(pk=draft.pk).delete()
    assert not CouncilSession.objects.filter(pk=draft.pk).exists()
    assert Outbox.objects.filter(pk=pk, kind="session_cancel").exists()
    with granted_roles("ctm_worker"), connection.cursor() as cursor:
        cursor.execute("SELECT public.ctm_session_delivery_current(%s)", [str(pk)])
        assert cursor.fetchone()[0] is True
