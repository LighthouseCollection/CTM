"""#242 / D-0058: GET /api/cases/<id>/timeline/ for the case-area timeline.

Every event carries an area (marriage, application, filing, assign, hearing,
decision, decree, comms), a civil date or pending, upcoming, a stable kind with
params (the screen shows EN/AR), an English title and description, and its
source. Council only; message bodies never appear. Fictional data.
"""
from datetime import date, timedelta

import pytest
from django.utils import timezone

from tribunal import models as m
from tribunal.services.communications import log_call
from tribunal.services.council import assign_case, create_session, place_agenda
from tests.test_case_delete import decided  # noqa: F401  (fixture)
from tests.test_core_policy_completion import granted_roles  # noqa: F401  (fixture)

pytestmark = pytest.mark.django_db
AREAS = {"marriage", "application", "filing", "assign", "hearing", "decision", "decree", "comms"}
FIELDS = {"id", "kind", "area", "date", "pending", "upcoming", "title", "description", "params", "source"}


def timeline(granted_roles, client, actor, case):
    client.force_login(actor)
    with granted_roles("ctm_app", session=True):
        return client.get(f"/api/cases/{case.pk}/timeline/")


def kinds(items):
    return [row["kind"] for row in items]


def test_every_event_has_an_area_date_and_text(granted_roles, client, people, decided):
    items = timeline(granted_roles, client, people["secretary"], decided).json()["items"]
    assert items and all(set(row) == FIELDS for row in items)
    assert {row["area"] for row in items} <= AREAS
    assert all(row["title"] and isinstance(row["params"], dict) for row in items)
    by_kind = {row["kind"]: row for row in items}
    assert by_kind["marriage"]["area"] == "marriage" and by_kind["marriage"]["date"] == "2010-05-01"
    assert by_kind["petition_submitted"]["area"] == "application"
    assert by_kind["decision_recorded"]["area"] == "decision"
    assert by_kind["decision_approved"]["area"] == "decision"
    assert by_kind["decree_issued"]["area"] == "decree"
    assert by_kind["decree_released"]["area"] == "decree"
    assert not any(row["upcoming"] or row["pending"] for row in items)


def test_assignment_hearings_and_communications(granted_roles, client, people, decided):
    party = decided.parties.get(slot="A")
    log_call(people["admin"], decided.pk, party.pk, timezone.now() - timedelta(days=1), "Reached", "Synthetic call")
    soon = timezone.localdate() + timedelta(days=10)
    upcoming = create_session(people["admin"], soon, location="Hall 2")
    if decided.assigned_member_id is None:
        assign_case(people["admin"], decided.pk, people["member"].pk, people["president"].pk)
    items = timeline(granted_roles, client, people["secretary"], decided).json()["items"]
    calls = [row for row in items if row["kind"] == "call_logged"]
    assert calls and calls[0]["area"] == "comms" and "Synthetic call" not in calls[0]["description"]
    assert any(row["kind"] == "manager_assigned" and row["area"] == "assign" for row in items)
    assert upcoming  # session exists; placing needs an open proceeding, covered below


def test_upcoming_hearing_is_marked_and_listed_first(granted_roles, client, people, ready_application):
    from tribunal.services.applications import submit_application
    app = ready_application
    submit_application(app.owner, app.pk, "timeline-242", {"accepted": True, "name": "John Smith"})
    app.refresh_from_db()
    assign_case(people["admin"], app.case_id, people["member"].pk, people["president"].pk)
    soon = timezone.localdate() + timedelta(days=10)
    session = create_session(people["admin"], soon, location="Hall 2")
    place_agenda(people["member"], session.pk, app.case_id)
    items = timeline(granted_roles, client, people["member"], app.case).json()["items"]
    first = items[0]
    assert first["kind"] == "hearing_scheduled" and first["area"] == "hearing"
    assert first["upcoming"] is True and first["date"] == soon.isoformat()
    dated = [row["date"] for row in items if row["date"]]
    assert dated == sorted(dated, reverse=True)  # newest first


def test_children_and_separation_come_from_the_filing(granted_roles, client, people, ready_application):
    from tribunal.services.applications import save_answers, submit_application
    app = ready_application
    answers = dict(app.revisions.get(number=app.current_version).answers, separation_date="2019-03-01",
                   children=[{"id": "6b0d6a8e-3f0e-4c11-9d39-2f4c2b1a7e01", "first_name": "Mary",
                              "last_name": "Smith", "date_of_birth": "2015-03-04", "gender": "F",
                              "lives_with": "Applicant"}])
    save_answers(app.owner, app.pk, answers, app.current_version)
    app.refresh_from_db()
    submit_application(app.owner, app.pk, "timeline-kids", {"accepted": True, "name": "John Smith"},
                       expected_version=app.current_version)
    app.refresh_from_db()
    items = timeline(granted_roles, client, people["secretary"], app.case).json()["items"]
    child = next(row for row in items if row["kind"] == "child_born")
    assert child["area"] == "marriage" and child["date"] == "2015-03-04" and child["params"]["first_name"] == "Mary"
    sep = next(row for row in items if row["kind"] == "separation")
    assert sep["area"] == "marriage" and sep["date"] == "2019-03-01"


def test_timeline_is_council_only(granted_roles, client, people, decided):
    owner = decided.parties.get(slot="A").account
    assert timeline(granted_roles, client, owner, decided).status_code == 403
