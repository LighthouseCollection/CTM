"""#175 / D-0043: a council seat is separate from the system role.

Any staff account can hold a seat; each seat is voting or non-voting. Changes
are append-only (each change is its own audit record), made only by admin,
secretary or president. The ballot refuses a vote from an account without a
voting seat; earlier votes stay as cast. With no change recorded, member and
president hold voting seats, and secretary and admin hold none.
"""
import json
from datetime import timedelta

import pytest
from django.db import DatabaseError, connection, transaction
from django.utils import timezone

from tribunal.models import Account, Vote
from tribunal.services.applications import submit_application
from tribunal.services.decisions import record_decision
from tests.test_core_policy_completion import granted_roles  # noqa: F401  (fixture)

pytestmark = pytest.mark.django_db


def seat(account):
    with connection.cursor() as cursor:
        cursor.execute("SELECT public.ctm_council_seat(%s)", [str(account.pk)])
        value = cursor.fetchone()[0]
    # Raw cursors may hand jsonb back as text.
    return json.loads(value) if isinstance(value, str) else value


def change(granted_roles, actor, account, seated, voting, created_at=None):
    with granted_roles("ctm_app", actor), connection.cursor() as cursor:
        cursor.execute(
            "INSERT INTO public.tribunal_councilseatchange(id,created_at,account_id,seated,voting,actor_id) "
            "VALUES (gen_random_uuid(), coalesce(%s, now()), %s, %s, %s, %s) RETURNING created_at",
            [created_at, str(account.pk), seated, voting, str(actor.pk)])
        return cursor.fetchone()[0]


@pytest.fixture
def decision(ready_application, people):
    app = ready_application
    submit_application(app.owner, app.pk, "seat-vote", {"accepted": True, "name": "John Smith"})
    app.refresh_from_db()
    return record_decision(people["admin"], app.proceeding_id, "diss-both", "Recorded grounds", {})


def vote(granted_roles, actor, decision, member=None, choice="approve"):
    with granted_roles("ctm_app", actor), connection.cursor() as cursor:
        cursor.execute("INSERT INTO public.tribunal_vote(id,created_at,decision_id,member_id,actor_id,choice) "
                       "VALUES (gen_random_uuid(), now(), %s, %s, %s, %s)",
                       [str(decision.pk), str((member or actor).pk), str(actor.pk), choice])


def test_default_seats_follow_the_role(people):
    assert seat(people["member"]) == {"seated": True, "voting": True}
    assert seat(people["president"]) == {"seated": True, "voting": True}
    for role in ["secretary", "admin", "applicant"]:
        assert seat(people[role]) == {"seated": False, "voting": False}


@pytest.mark.parametrize("changer", ["admin", "secretary", "president"])
def test_admin_secretary_and_president_change_seats_and_the_latest_counts(granted_roles, people, changer):
    admin = people["admin"]
    change(granted_roles, people[changer], admin, True, True)
    assert seat(admin) == {"seated": True, "voting": True}
    change(granted_roles, people[changer], admin, True, False)
    assert seat(admin) == {"seated": True, "voting": False}
    change(granted_roles, people[changer], people["member"], False, False)
    assert seat(people["member"]) == {"seated": False, "voting": False}


@pytest.mark.parametrize("changer", ["member", "applicant"])
def test_member_and_applicant_cannot_change_seats(granted_roles, people, changer):
    with pytest.raises(DatabaseError):
        change(granted_roles, people[changer], people[changer], True, True)


def test_applicants_never_hold_a_seat_and_voting_needs_a_seat(granted_roles, people):
    with pytest.raises(DatabaseError):
        change(granted_roles, people["admin"], people["applicant"], True, False)
    with pytest.raises(DatabaseError):
        change(granted_roles, people["admin"], people["secretary"], False, True)


def test_the_actor_is_the_signed_in_account(granted_roles, people):
    with pytest.raises(DatabaseError):
        with granted_roles("ctm_app", people["admin"]), connection.cursor() as cursor:
            cursor.execute("INSERT INTO public.tribunal_councilseatchange(id,created_at,account_id,seated,voting,actor_id) "
                           "VALUES (gen_random_uuid(), now(), %s, true, true, %s)",
                           [str(people["admin"].pk), str(people["president"].pk)])


def test_change_time_is_the_database_clock(granted_roles, people):
    stored = change(granted_roles, people["admin"], people["admin"], True, True,
                    created_at=timezone.now() - timedelta(days=30))
    assert abs((stored - timezone.now()).total_seconds()) < 60


def test_changes_are_append_only(granted_roles, people):
    change(granted_roles, people["admin"], people["admin"], True, True)
    for statement in ["UPDATE public.tribunal_councilseatchange SET voting=false",
                      "DELETE FROM public.tribunal_councilseatchange"]:
        with pytest.raises(DatabaseError), transaction.atomic(), connection.cursor() as cursor:
            cursor.execute(statement)
    assert seat(people["admin"]) == {"seated": True, "voting": True}


def test_staff_read_seats_and_applicants_get_nothing(granted_roles, people):
    change(granted_roles, people["admin"], people["admin"], True, True)
    for role, expected in [("member", 1), ("secretary", 1), ("applicant", 0)]:
        with granted_roles("ctm_app", people[role]), connection.cursor() as cursor:
            cursor.execute("SELECT count(*) FROM public.tribunal_councilseatchange")
            assert cursor.fetchone()[0] == expected, role


def test_ballot_needs_a_voting_seat(granted_roles, people, decision):
    # A member with the default voting seat votes; the secretary has no seat.
    vote(granted_roles, people["member"], decision)
    with pytest.raises(DatabaseError):
        vote(granted_roles, people["secretary"], decision)
    # Recording for another member also needs that member's voting seat.
    with pytest.raises(DatabaseError):
        vote(granted_roles, people["admin"], decision, member=people["secretary"])


def test_non_voting_seat_cannot_vote_and_earlier_votes_stay(granted_roles, people, decision):
    member = people["member"]
    vote(granted_roles, member, decision, choice="deny")
    change(granted_roles, people["president"], member, True, False)
    with pytest.raises(DatabaseError):
        vote(granted_roles, member, decision)
    assert list(Vote.objects.filter(member=member).values_list("choice", flat=True)) == ["deny"]


def test_an_admin_with_a_voting_seat_can_vote(granted_roles, people, decision):
    admin = people["admin"]
    change(granted_roles, people["secretary"], admin, True, True)
    vote(granted_roles, admin, decision)
    assert Vote.objects.filter(member=admin).count() == 1


def test_inactive_account_has_no_voting_seat(people):
    Account.objects.filter(pk=people["member"].pk).update(is_active=False)
    assert seat(people["member"]) == {"seated": False, "voting": False}


def test_seat_function_grants():
    with connection.cursor() as cursor:
        cursor.execute("""SELECT coalesce(r.rolname, 'PUBLIC') FROM pg_proc p,
            LATERAL aclexplode(coalesce(p.proacl, acldefault('f', p.proowner))) access
            LEFT JOIN pg_roles r ON r.oid = access.grantee
            WHERE p.oid = 'public.ctm_council_seat(uuid)'::regprocedure
              AND access.privilege_type = 'EXECUTE' AND access.grantee <> p.proowner ORDER BY 1""")
        assert [row[0] for row in cursor.fetchall()] == ["ctm_app"]
