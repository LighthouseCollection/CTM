"""#229 / D-0053 data: the attendance list shows every council seat holder.

GET /api/sessions/<id>/attendance/ adds `roster`: president, secretary and
members plus any other seat holder (D-0043, e.g. an admin with a seat), in
roster order, each with title, voting flag, photo_url and recorded attendance.
The hearing roster carries the same fields. `items` stays as it was.
"""
from datetime import date

import pytest

from tribunal.services.council import create_session, record_attendance
from tribunal.services.council_seats import set_seat
from tests.test_core_policy_completion import granted_roles  # noqa: F401  (fixture)

pytestmark = pytest.mark.django_db
FIELDS = {"member_id", "member_name", "member_role", "member_active", "title", "voting", "photo_url",
          "present", "actor_id", "timestamp"}


def get(granted_roles, client, actor, url):
    client.force_login(actor)
    with granted_roles("ctm_app", session=True):
        return client.get(url)


@pytest.fixture
def session(people):
    return create_session(people["admin"], date(2031, 3, 4), location="Hall 2")


def test_roster_lists_seat_holders_with_title_voting_and_photo(granted_roles, client, people, session):
    set_seat(people["president"], people["admin"].pk, seated=True, voting=True)
    set_seat(people["president"], people["member"].pk, seated=True, voting=False)
    record_attendance(people["admin"], session.pk, people["member"].pk, True)
    data = get(granted_roles, client, people["secretary"], f"/api/sessions/{session.pk}/attendance/").json()
    assert len(data["items"]) == 1 and data["items"][0]["member_id"] == str(people["member"].pk)  # unchanged
    roster = data["roster"]
    assert all(set(row) == FIELDS for row in roster)
    by_id = {row["member_id"]: row for row in roster}
    assert str(people["admin"].pk) in by_id and str(people["applicant"].pk) not in by_id
    assert [row["title"] for row in roster][:2] == ["presiding", "secretary"]
    assert by_id[str(people["admin"].pk)]["voting"] is True and by_id[str(people["admin"].pk)]["title"] == "member"
    assert by_id[str(people["member"].pk)]["voting"] is False and by_id[str(people["member"].pk)]["present"] is True
    assert by_id[str(people["president"].pk)]["present"] is None
    assert all(row["photo_url"] is None for row in roster)  # CTM stores no council photos


def test_unseated_admin_is_not_on_the_roster(granted_roles, client, people, session):
    roster = get(granted_roles, client, people["secretary"], f"/api/sessions/{session.pk}/attendance/").json()["roster"]
    assert str(people["admin"].pk) not in {row["member_id"] for row in roster}


def test_applicant_cannot_read_attendance(granted_roles, client, people, session):
    assert get(granted_roles, client, people["applicant"], f"/api/sessions/{session.pk}/attendance/").status_code == 403
