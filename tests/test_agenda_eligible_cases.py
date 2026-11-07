"""#230: data for the session "Case to be Assigned" / "Add hearing case" picker.

GET /api/sessions/<id>/eligible-cases/?part=1|2 lists the cases that can go on
that part of the agenda, with number, parties, filed date, grounds, status,
assigned member and a recommendation preview. POST .../agenda/batch/ places
several cases in one call, all or none. Fictional data only.
"""
from datetime import date

import pytest

from tribunal import models as m
from tribunal.services.applications import submit_application
from tribunal.services.council import assign_case, create_session, hear_case, place_agenda
from tests.test_core_policy_completion import granted_roles  # noqa: F401  (fixture)

pytestmark = pytest.mark.django_db
ROW = {"id", "number", "party_names", "filed_at", "grounds", "status", "assigned_member_id",
       "assigned_member", "recommendation_preview"}


def call(granted_roles, client, actor, method, url, data=None):
    client.force_login(actor)
    with granted_roles("ctm_app", session=True):
        if method == "get":
            return client.get(url)
        return client.post(url, data or {}, content_type="application/json")


@pytest.fixture
def two_cases(ready_application):
    first = ready_application
    submit_application(first.owner, first.pk, "elig-1", {"accepted": True, "name": "John Smith"})
    first.refresh_from_db()
    return first


@pytest.fixture
def session(people):
    return create_session(people["admin"], date(2031, 5, 6), location="Hall 2")


def test_part_one_lists_unassigned_open_cases_with_picker_fields(granted_roles, client, people, two_cases, session):
    rows = call(granted_roles, client, people["secretary"], "get",
                f"/api/sessions/{session.pk}/eligible-cases/?part=1").json()["items"]
    assert [row["id"] for row in rows] == [str(two_cases.case_id)]
    row = rows[0]
    assert set(row) == ROW
    assert row["number"] == two_cases.case.number and row["status"] == "open" and row["assigned_member"] is None
    assert row["filed_at"] and row["grounds"] == ["infidelity"] and row["party_names"]
    assert row["recommendation_preview"] is None


def test_part_two_lists_assigned_cases_and_a_member_sees_only_their_own(granted_roles, client, people, two_cases, session):
    assign_case(people["admin"], two_cases.case_id, people["member"].pk, people["president"].pk)
    assert call(granted_roles, client, people["secretary"], "get",
                f"/api/sessions/{session.pk}/eligible-cases/?part=1").json()["items"] == []
    mine = call(granted_roles, client, people["member"], "get",
                f"/api/sessions/{session.pk}/eligible-cases/?part=2").json()["items"]
    assert [row["id"] for row in mine] == [str(two_cases.case_id)]
    assert mine[0]["assigned_member_id"] == str(people["member"].pk)
    other = m.Account.objects.create_user(email="other.member@example.test", role="member",
                                          first_name="Other", last_name="Member")
    assert call(granted_roles, client, other, "get",
                f"/api/sessions/{session.pk}/eligible-cases/?part=2").json()["items"] == []


def test_placed_cases_drop_out_and_the_preview_shows_the_last_recommendation(granted_roles, client, people, two_cases,
                                                                              session):
    assign_case(people["admin"], two_cases.case_id, people["member"].pk, people["president"].pk)
    earlier = create_session(people["admin"], date(2031, 4, 1), location="Hall 1")
    hearing = hear_case(people["member"], place_agenda(people["member"], earlier.pk, two_cases.case_id).pk)
    m.HearingOutcome.objects.create(hearing=hearing, actor=people["member"], internal_text="Synthetic",
                                    recommendations="Recommend a further interview. " * 20)
    rows = call(granted_roles, client, people["secretary"], "get",
                f"/api/sessions/{session.pk}/eligible-cases/?part=2").json()["items"]
    assert rows[0]["recommendation_preview"].startswith("Recommend a further interview.")
    assert len(rows[0]["recommendation_preview"]) <= 200
    place_agenda(people["member"], session.pk, two_cases.case_id)
    assert call(granted_roles, client, people["secretary"], "get",
                f"/api/sessions/{session.pk}/eligible-cases/?part=2").json()["items"] == []


def test_bad_part_and_applicant_are_refused(granted_roles, client, people, session):
    assert call(granted_roles, client, people["secretary"], "get",
                f"/api/sessions/{session.pk}/eligible-cases/?part=3").status_code == 422
    assert call(granted_roles, client, people["applicant"], "get",
                f"/api/sessions/{session.pk}/eligible-cases/?part=1").status_code == 403


def test_batch_places_several_cases_at_once(granted_roles, client, people, two_cases, session):
    other_case = m.Case.objects.create(number="20990101-07", origin="synthetic", status="open")
    m.Proceeding.objects.create(case=other_case)
    response = call(granted_roles, client, people["secretary"], "post", f"/api/sessions/{session.pk}/agenda/batch/",
                    {"part": 1, "case_ids": [str(two_cases.case_id), str(other_case.pk)]})
    assert response.status_code == 201, response.content
    assert {row["case_id"] for row in response.json()["items"]} == {str(two_cases.case_id), str(other_case.pk)}
    assert m.AgendaItem.objects.filter(session=session, part=1).count() == 2


def test_batch_is_all_or_none(granted_roles, client, people, two_cases, session):
    closed = m.Case.objects.create(number="20990101-08", origin="synthetic", status="closed")
    m.Proceeding.objects.create(case=closed, status="closed")
    response = call(granted_roles, client, people["secretary"], "post", f"/api/sessions/{session.pk}/agenda/batch/",
                    {"part": 1, "case_ids": [str(two_cases.case_id), str(closed.pk)]})
    assert response.status_code == 422
    assert "20990101-08" in response.json()["messages"][0]
    assert not m.AgendaItem.objects.filter(session=session).exists()


@pytest.mark.parametrize("ids", [[], "x", ["not-a-uuid"]])
def test_batch_input_is_checked(granted_roles, client, people, session, ids):
    response = call(granted_roles, client, people["secretary"], "post", f"/api/sessions/{session.pk}/agenda/batch/",
                    {"part": 1, "case_ids": ids})
    assert response.status_code == 422
