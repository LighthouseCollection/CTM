"""#170 AC-5 (council Home), part 1: dashboard session card, my cases, members.

Council roles only, deny by default. The members list carries counts only,
never applicant data; a count below the privacy threshold (5, interim) is
null with suppressed: true. The session answer counts follow #116: only
secretary, president and admin see how many confirmed.
"""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from django.utils import timezone

from tribunal import models as m
from tribunal.services.applications import submit_application
from tribunal.services.council import create_session, place_agenda
from tribunal.services.session_reminders import answer_session
from tests.test_core_policy_completion import granted_roles  # noqa: F401  (fixture)

pytestmark = pytest.mark.django_db
LA = ZoneInfo("America/Los_Angeles")


def get(granted_roles, client, actor, url):
    if actor is not None:
        client.force_login(actor)
    with granted_roles("ctm_app", session=True):
        return client.get(url)


@pytest.fixture
def filed(ready_application):
    app = ready_application
    submit_application(app.owner, app.pk, "home-170", {"accepted": True, "name": "John Smith"})
    app.refresh_from_db()
    return app


@pytest.fixture
def upcoming(people, filed, settings):
    settings.EMAIL_HOST = ""
    day = (timezone.now() + timedelta(days=9)).astimezone(LA).date()
    session = create_session(people["admin"], day, starts_at=datetime(day.year, day.month, day.day, 10, 30, tzinfo=LA),
                             location="Hall 2")
    m.Case.objects.filter(pk=filed.case_id).update(assigned_member=people["member"])
    place_agenda(people["member"], session.pk, filed.case_id)
    return session


def test_dashboard_session_card_has_time_place_agenda_and_answers(granted_roles, client, people, upcoming):
    answer_session(people["member"], upcoming.pk, "attend")
    card = get(granted_roles, client, people["secretary"], "/api/dashboard/").json()["upcoming_sessions"][0]
    assert card["id"] == str(upcoming.pk)
    assert datetime.fromisoformat(card["starts_at"]) == upcoming.starts_at and card["location"] == "Hall 2"
    assert card["agenda_count"] == 1
    assert card["my_answer"] is None and card["confirmed"] == 1 and card["invited"] >= 4
    mine = get(granted_roles, client, people["member"], "/api/dashboard/").json()["upcoming_sessions"][0]
    assert mine["my_answer"] == "attend"
    assert mine["confirmed"] is None and mine["invited"] is None  # #116: a member sees only their own answer


def test_my_cases_rows_carry_names_status_and_next_step(granted_roles, client, people, filed, upcoming):
    rows = get(granted_roles, client, people["member"], "/api/cases/?mine=1").json()["items"]
    assert [row["id"] for row in rows] == [str(filed.case_id)]
    row = rows[0]
    assert row["status"] == "open" and row["applicant_name"] and "respondent_name" in row
    assert row["next_step"] == "case.next.completeness_review"
    assert get(granted_roles, client, people["president"], "/api/cases/?mine=1").json()["items"] == []


def test_members_list_titles_and_counts(granted_roles, client, people, filed):
    rows = {row["id"]: row for row in get(granted_roles, client, people["member"], "/api/dashboard/members/").json()["items"]}
    assert rows[str(people["president"].pk)]["title"] == "presiding"
    assert rows[str(people["secretary"].pk)]["title"] == "secretary"
    assert rows[str(people["member"].pk)]["title"] == "member"
    assert str(people["applicant"].pk) not in rows and str(people["admin"].pk) not in rows  # admin holds no seat
    assert set(rows[str(people["member"].pk)]) == {"id", "name", "title", "photo_url", "active_cases", "suppressed"}


def test_members_counts_below_threshold_are_suppressed(granted_roles, client, people, filed):
    m.Case.objects.filter(pk=filed.case_id).update(assigned_member=people["member"])
    row = next(r for r in get(granted_roles, client, people["secretary"], "/api/dashboard/members/").json()["items"]
               if r["id"] == str(people["member"].pk))
    assert row["active_cases"] is None and row["suppressed"] is True
    for n in range(5):
        m.Case.objects.create(number=f"HOME-{n}", origin="synthetic", status="open", assigned_member=people["member"])
    row = next(r for r in get(granted_roles, client, people["secretary"], "/api/dashboard/members/").json()["items"]
               if r["id"] == str(people["member"].pk))
    assert row["active_cases"] == 6 and row["suppressed"] is False


def test_members_list_is_council_only(granted_roles, client, people):
    assert get(granted_roles, client, people["applicant"], "/api/dashboard/members/").status_code == 403
    client.logout()
    assert get(granted_roles, client, None, "/api/dashboard/members/").status_code == 401
