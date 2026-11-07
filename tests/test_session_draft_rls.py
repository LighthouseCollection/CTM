"""#224 / D-0052 database part: a council session moves between Draft and In
progress (planned) any time before it is adjourned, by admin, president or
secretary. Closing stays admin and secretary only. Run as the restricted role.
"""
from datetime import date

import pytest
from django.db import DatabaseError, connection, transaction
from django.utils import timezone

from tribunal.models import CouncilSession
from tests.test_core_policy_completion import granted_roles  # noqa: F401  (fixture)

pytestmark = pytest.mark.django_db


@pytest.fixture
def session(db):
    return CouncilSession.objects.create(date=date(2030, 8, 9), state="planned")


def set_state(granted_roles, actor, session, state):
    with granted_roles("ctm_app", actor), connection.cursor() as cursor:
        cursor.execute("UPDATE public.tribunal_councilsession SET state=%s WHERE id=%s", [state, str(session.pk)])
        assert cursor.rowcount == 1


def state(session):
    return CouncilSession.objects.get(pk=session.pk).state


@pytest.mark.parametrize("role", ["admin", "president", "secretary"])
def test_in_progress_session_goes_back_to_draft_and_forward_again(granted_roles, people, session, role):
    set_state(granted_roles, people[role], session, "draft")
    assert state(session) == "draft"
    set_state(granted_roles, people[role], session, "planned")
    assert state(session) == "planned"


@pytest.mark.parametrize("role", ["member", "applicant"])
def test_member_and_applicant_cannot_change_session_state(granted_roles, people, session, role):
    with pytest.raises(DatabaseError):
        set_state(granted_roles, people[role], session, "draft")
    assert state(session) == "planned"


def test_adjourned_session_cannot_go_back_to_draft(granted_roles, people, session):
    CouncilSession.objects.filter(pk=session.pk).update(adjourned_at=timezone.now())
    for role in ["admin", "president", "secretary"]:
        with pytest.raises(DatabaseError):
            set_state(granted_roles, people[role], session, "draft")
    assert state(session) == "planned"


def test_closed_session_cannot_go_back_to_draft(granted_roles, people, session):
    CouncilSession.objects.filter(pk=session.pk).update(state="closed", closed_at=timezone.now())
    with pytest.raises(DatabaseError):
        set_state(granted_roles, people["admin"], session, "draft")
    assert state(session) == "closed"


def test_president_cannot_close_a_session(granted_roles, people, session):
    # The new rule covers Draft and In progress only; closing keeps its old rule.
    with pytest.raises(DatabaseError):
        with granted_roles("ctm_app", people["president"]), connection.cursor() as cursor:
            cursor.execute("UPDATE public.tribunal_councilsession SET state='closed', closed_at=now() WHERE id=%s",
                           [str(session.pk)])
    assert state(session) == "planned"


@pytest.mark.parametrize("role,allowed", [("admin", True), ("secretary", True), ("president", False), ("member", False)])
def test_draft_session_can_be_created_by_admin_and_secretary(granted_roles, people, role, allowed):
    def create():
        with granted_roles("ctm_app", people[role]), connection.cursor() as cursor:
            cursor.execute("INSERT INTO public.tribunal_councilsession(id,created_at,date,location,state,ics_sequence) "
                           "VALUES (gen_random_uuid(), now(), %s, '', 'draft', 0)", [date(2030, 9, 1)])
    if allowed:
        create()
        assert CouncilSession.objects.filter(date=date(2030, 9, 1), state="draft").exists()
    else:
        with pytest.raises(DatabaseError), transaction.atomic():
            create()
