"""#237 / D-0056 undo window: inside the assignment context, an assignment
recorder under an active president may discard the parties' not-yet-due
assignment notices for that case, so an accidental click sends nothing.
Only discarded_at may change. Run as the restricted runtime role.
"""
from datetime import timedelta

import pytest
from django.db import DatabaseError, connection, transaction
from django.utils import timezone

from tribunal.db.context import database_settings
from tribunal.models import Case, Outbox, Party
from tribunal.services.applications import submit_application
from tribunal.services.council import assign_case
from tests.test_core_policy_completion import granted_roles  # noqa: F401  (fixture)

pytestmark = pytest.mark.django_db


@pytest.fixture
def managed(ready_application, people):
    app = ready_application
    submit_application(app.owner, app.pk, "discard", {"accepted": True, "name": "John Smith"})
    app.refresh_from_db()
    assign_case(people["admin"], app.case_id, people["member"].pk, people["president"].pk)
    return Case.objects.get(pk=app.case_id)


def notice(case, *, kind="assignment_changed", recipient=None, due=timedelta(minutes=5), **extra):
    recipient = recipient or Party.objects.filter(case=case, account__isnull=False).first().account
    return Outbox.objects.create(key=f"{kind}:{case.pk}:{recipient.pk}:{timezone.now().timestamp()}", kind=kind,
                                 case=case, recipient=recipient, payload={}, due_at=timezone.now() + due, **extra)


def discard(granted_roles, actor, case, row, *, president, target=None, member="", sql=None):
    context = {"ctm.core_operation": "assignment", "ctm.core_target": str(target or case.pk),
               "ctm.assignment_member": member, "ctm.assignment_president": str(president.pk)}
    with granted_roles("ctm_app", actor), database_settings(context), connection.cursor() as cursor:
        cursor.execute(sql or "UPDATE public.tribunal_outbox SET discarded_at=now() WHERE id=%s", [str(row.pk)])
        assert cursor.rowcount == 1


def refused(*args, **kwargs):
    row = args[3]
    with pytest.raises((DatabaseError, AssertionError)), transaction.atomic():
        discard(*args, **kwargs)
    assert Outbox.objects.get(pk=row.pk).discarded_at is None


@pytest.mark.parametrize("recorder", ["admin", "secretary"])
@pytest.mark.parametrize("kind", ["assignment_changed", "case_unassigned"])
def test_recorder_discards_a_parties_notice_inside_the_window(granted_roles, people, managed, recorder, kind):
    row = notice(managed, kind=kind)
    discard(granted_roles, people[recorder], managed, row, president=people["president"])
    assert Outbox.objects.get(pk=row.pk).discarded_at is not None


def test_change_context_with_a_member_also_discards(granted_roles, people, managed):
    row = notice(managed)
    discard(granted_roles, people["admin"], managed, row, president=people["president"], member=str(people["member"].pk))
    assert Outbox.objects.get(pk=row.pk).discarded_at is not None


def test_due_notice_cannot_be_discarded(granted_roles, people, managed):
    refused(granted_roles, people["admin"], managed, notice(managed, due=-timedelta(seconds=1)), president=people["president"])


def test_delivered_notice_cannot_be_discarded(granted_roles, people, managed):
    refused(granted_roles, people["admin"], managed, notice(managed, delivered_at=timezone.now()), president=people["president"])


def test_other_kinds_cannot_be_discarded(granted_roles, people, managed):
    refused(granted_roles, people["admin"], managed, notice(managed, kind="answer_changed"), president=people["president"])


def test_only_party_recipients(granted_roles, people, managed):
    refused(granted_roles, people["admin"], managed, notice(managed, recipient=people["secretary"]), president=people["president"])


def test_only_discarded_at_may_change(granted_roles, people, managed):
    refused(granted_roles, people["admin"], managed, notice(managed), president=people["president"],
            sql="UPDATE public.tribunal_outbox SET discarded_at=now(), last_error='x' WHERE id=%s")
    refused(granted_roles, people["admin"], managed, notice(managed), president=people["president"],
            sql="UPDATE public.tribunal_outbox SET discarded_at=now()-interval '1 day' WHERE id=%s")


def test_needs_the_assignment_context_for_this_case(granted_roles, people, managed):
    row = notice(managed)
    refused(granted_roles, people["admin"], managed, row, president=people["president"],
            target="00000000-0000-4000-8000-000000000237")
    refused(granted_roles, people["admin"], managed, row, president=people["secretary"])
    with pytest.raises(DatabaseError), transaction.atomic():
        with granted_roles("ctm_app", people["admin"]), connection.cursor() as cursor:
            cursor.execute("UPDATE public.tribunal_outbox SET discarded_at=now() WHERE id=%s", [str(row.pk)])
    assert Outbox.objects.get(pk=row.pk).discarded_at is None


@pytest.mark.parametrize("role", ["member", "applicant"])
def test_member_and_applicant_cannot_discard(granted_roles, people, managed, role):
    refused(granted_roles, people[role], managed, notice(managed), president=people["president"])
