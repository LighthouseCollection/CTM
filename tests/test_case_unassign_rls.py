"""#237 / D-0056 database part: an audited unassign, so Undo works on a first
assignment. Under op 'assignment' with an empty ctm.assignment_member, an
assignment recorder under an active president may clear the case manager of an
open case that is not scheduled for a hearing in a draft or planned session.
Run as the restricted runtime role.
"""
from datetime import date

import pytest
from django.db import DatabaseError, connection, transaction

from tribunal.db.context import database_settings
from tribunal.models import AgendaItem, Case, CaseAssignment, CouncilSession
from tribunal.services.applications import submit_application
from tribunal.services.council import assign_case
from tests.test_core_policy_completion import granted_roles  # noqa: F401  (fixture)

pytestmark = pytest.mark.django_db


@pytest.fixture
def managed(ready_application, people):
    app = ready_application
    submit_application(app.owner, app.pk, "unassign", {"accepted": True, "name": "John Smith"})
    app.refresh_from_db()
    assign_case(people["admin"], app.case_id, people["member"].pk, people["president"].pk)
    return Case.objects.get(pk=app.case_id)


def unassign(granted_roles, actor, case, *, president, member="", sql=None):
    context = {"ctm.core_operation": "assignment", "ctm.core_target": str(case.pk),
               "ctm.assignment_member": member, "ctm.assignment_president": str(president.pk)}
    with granted_roles("ctm_app", actor), database_settings(context), connection.cursor() as cursor:
        cursor.execute(sql or "UPDATE public.tribunal_case SET assigned_member_id=NULL WHERE id=%s", [str(case.pk)])
        assert cursor.rowcount == 1


def manager(case):
    return Case.objects.get(pk=case.pk).assigned_member_id


@pytest.mark.parametrize("recorder", ["admin", "secretary"])
def test_recorder_clears_the_case_manager_and_history_stays(granted_roles, people, managed, recorder):
    history = CaseAssignment.objects.filter(case=managed).count()
    unassign(granted_roles, people[recorder], managed, president=people["president"])
    assert manager(managed) is None
    assert CaseAssignment.objects.filter(case=managed).count() == history


@pytest.mark.parametrize("role", ["member", "applicant"])
def test_member_and_applicant_cannot_unassign(granted_roles, people, managed, role):
    with pytest.raises((DatabaseError, AssertionError)):
        unassign(granted_roles, people[role], managed, president=people["president"])
    assert manager(managed) == people["member"].pk


def test_unassign_needs_an_active_president(granted_roles, people, managed):
    with pytest.raises(DatabaseError):
        unassign(granted_roles, people["admin"], managed, president=people["secretary"])
    assert manager(managed) == people["member"].pk


def test_null_manager_needs_the_empty_member_context(granted_roles, people, managed):
    # An assignment context naming a member can never write NULL.
    with pytest.raises(DatabaseError):
        unassign(granted_roles, people["admin"], managed, president=people["president"], member=str(people["member"].pk))
    assert manager(managed) == people["member"].pk


def test_case_scheduled_for_a_hearing_cannot_be_unassigned(granted_roles, people, managed):
    session = CouncilSession.objects.create(date=date(2030, 10, 4), state="planned")
    AgendaItem.objects.create(session=session, case=managed, part=2, state="scheduled")
    with pytest.raises(DatabaseError):
        unassign(granted_roles, people["admin"], managed, president=people["president"])
    assert manager(managed) == people["member"].pk


def test_closed_case_cannot_be_unassigned(granted_roles, people, managed):
    Case.objects.filter(pk=managed.pk).update(status="closed")
    with pytest.raises(DatabaseError):
        unassign(granted_roles, people["admin"], managed, president=people["president"])
    assert manager(managed) == people["member"].pk


def test_unassign_cannot_change_anything_else(granted_roles, people, managed):
    with pytest.raises(DatabaseError), transaction.atomic():
        unassign(granted_roles, people["admin"], managed, president=people["president"],
                 sql="UPDATE public.tribunal_case SET assigned_member_id=NULL, status='closed' WHERE id=%s")
    assert manager(managed) == people["member"].pk


def test_unassign_targets_only_the_context_case(granted_roles, people, managed):
    context = {"ctm.core_operation": "assignment", "ctm.core_target": "00000000-0000-4000-8000-000000000237",
               "ctm.assignment_member": "", "ctm.assignment_president": str(people["president"].pk)}
    with pytest.raises((DatabaseError, AssertionError)):
        with granted_roles("ctm_app", people["admin"]), database_settings(context), connection.cursor() as cursor:
            cursor.execute("UPDATE public.tribunal_case SET assigned_member_id=NULL WHERE id=%s", [str(managed.pk)])
            assert cursor.rowcount == 1
    assert manager(managed) == people["member"].pk
