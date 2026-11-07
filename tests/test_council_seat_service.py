"""#175 / D-0043 backend: council seats in the service, ballot, tally and API.

The database part (ctm_council_seat, the vote guard) is tested in
tests/test_council_seats.py. Here: admin, secretary and president change
seats; a voting seat (not the role) decides who may vote; the decision tally
counts current voting seats; seated accounts join the council lists.
"""
import pytest
from django.core.exceptions import PermissionDenied, ValidationError

from tribunal import models as m
from tribunal.projections import decision_data
from tribunal.services.applications import submit_application
from tribunal.services.council_seats import council_seat, set_seat
from tribunal.services.decisions import cast_vote, record_decision
from tests.test_core_policy_completion import granted_roles  # noqa: F401  (fixture)

pytestmark = pytest.mark.django_db


@pytest.fixture
def decision(ready_application, people):
    app = ready_application
    submit_application(app.owner, app.pk, "seat-vote", {"accepted": True, "name": "John Smith"})
    app.refresh_from_db()
    return record_decision(people["admin"], app.proceeding_id, "diss-both", "Recorded grounds",
                           {str(app.party_id): "certificate"})


def test_defaults_member_and_president_vote_secretary_and_admin_hold_no_seat(people):
    assert council_seat(people["member"]) == {"seated": True, "voting": True}
    assert council_seat(people["president"]) == {"seated": True, "voting": True}
    assert council_seat(people["secretary"]) == {"seated": False, "voting": False}
    assert council_seat(people["admin"]) == {"seated": False, "voting": False}
    assert council_seat(people["applicant"]) == {"seated": False, "voting": False}


@pytest.mark.parametrize("editor", ["admin", "secretary", "president"])
def test_officers_give_an_admin_a_voting_seat(people, editor):
    assert set_seat(people[editor], people["admin"].pk, seated=True, voting=True) == {"seated": True, "voting": True}
    assert council_seat(people["admin"]) == {"seated": True, "voting": True}
    change = m.CouncilSeatChange.objects.get(account=people["admin"])
    assert change.actor_id == people[editor].pk
    assert m.AuditEvent.objects.filter(action="council_seat_changed", source_id=change.pk).exists()


@pytest.mark.parametrize("editor", ["member", "applicant"])
def test_member_and_applicant_cannot_change_seats(people, editor):
    with pytest.raises(PermissionDenied):
        set_seat(people[editor], people["admin"].pk, seated=True, voting=True)
    assert not m.CouncilSeatChange.objects.exists()


def test_seat_rules(people):
    with pytest.raises(ValidationError, match="seat"):
        set_seat(people["admin"], people["member"].pk, seated=False, voting=True)
    with pytest.raises(ValidationError):
        set_seat(people["admin"], people["member"].pk, seated="yes", voting=True)
    with pytest.raises(ValidationError, match="council"):
        set_seat(people["admin"], people["applicant"].pk, seated=True, voting=False)
    assert not m.CouncilSeatChange.objects.exists()


def test_voting_seat_not_role_decides_the_ballot(people, decision):
    # An admin with a voting seat votes; a member made non-voting gets a clean refusal.
    set_seat(people["president"], people["admin"].pk, seated=True, voting=True)
    assert cast_vote(people["admin"], decision.pk, "approve").member_id == people["admin"].pk
    set_seat(people["president"], people["member"].pk, seated=True, voting=False)
    with pytest.raises(PermissionDenied, match="voting seat"):
        cast_vote(people["member"], decision.pk, "approve")
    with pytest.raises(PermissionDenied, match="voting seat"):
        cast_vote(people["secretary"], decision.pk, "approve")  # no seat by default
    assert set(m.Vote.objects.values_list("member_id", flat=True)) == {people["admin"].pk}


def test_tally_counts_current_voting_seats_and_keeps_earlier_votes(people, decision):
    cast_vote(people["member"], decision.pk, "approve")
    cast_vote(people["president"], decision.pk, "deny")
    data = decision_data(decision, people["secretary"])
    assert data["tally"] == {"approve": 1, "deny": 1, "abstain": 0, "voting_seats": 2}
    set_seat(people["admin"], people["member"].pk, seated=True, voting=False)
    data = decision_data(decision, people["secretary"])
    assert data["tally"] == {"approve": 1, "deny": 1, "abstain": 0, "voting_seats": 1}  # earlier vote stays


def test_seated_admin_joins_the_council_lists(people):
    from tribunal.services.council import attendance_roster_for, create_session
    from datetime import date
    set_seat(people["secretary"], people["admin"].pk, seated=True, voting=False)
    session = create_session(people["admin"], date(2030, 1, 2))
    roster = [member.pk for member, _ in attendance_roster_for(people["admin"], session.pk)]
    assert people["admin"].pk in roster and people["member"].pk in roster


def test_api_lists_and_changes_seats(granted_roles, people, client):
    client.force_login(people["secretary"])
    with granted_roles("ctm_app", session=True):
        rows = {row["id"]: row for row in client.get("/api/council/seats/").json()["items"]}
        assert rows[str(people["member"].pk)]["voting"] is True
        assert rows[str(people["admin"].pk)]["seated"] is False
        assert str(people["applicant"].pk) not in rows
        response = client.post(f"/api/council/seats/{people['admin'].pk}/", {"seated": True, "voting": True},
                               content_type="application/json")
        assert response.status_code == 200, response.content
        assert response.json() == {"id": str(people["admin"].pk), "seated": True, "voting": True}
        members = {row["id"] for row in client.get("/api/council/members/").json()["items"]}
        assert str(people["admin"].pk) in members
    client.force_login(people["member"])
    with granted_roles("ctm_app", session=True):
        assert client.post(f"/api/council/seats/{people['admin'].pk}/", {"seated": False, "voting": False},
                           content_type="application/json").status_code == 403
    client.force_login(people["applicant"])
    with granted_roles("ctm_app", session=True):
        assert client.get("/api/council/seats/").status_code == 403
