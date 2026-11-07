"""#170 AC-5 part 2: GET /api/statistics/summary/?year=.

Council roles only. Counts only, never applicant rows or links. Grounds come
from submitted petition answers only (never Professional Assessments), as
D-0035 codes. A count below the privacy threshold (5) is null + suppressed.
"""
from datetime import date

import pytest
from django.utils import timezone

from tribunal import models as m
from tests.test_core_policy_completion import granted_roles  # noqa: F401  (fixture)

pytestmark = pytest.mark.django_db
YEAR = timezone.localdate().year


def get(granted_roles, client, actor, url="/api/statistics/summary/"):
    if actor is not None:
        client.force_login(actor)
    with granted_roles("ctm_app", session=True):
        return client.get(url)


def make_cases(people, n, *, member=None, grounds=("abandonment",), prefix="S"):
    q = m.QuestionnaireVersion.objects.filter(purpose="petition").order_by("-number").first()
    for i in range(n):
        owner = m.Account.objects.create_user(email=f"{prefix.lower()}{i}@example.test", email_verified=True)
        case = m.Case.objects.create(number=f"{prefix}-{i:02d}", origin="synthetic", status="open",
                                     marriage_date=date(2010, 1, 1), assigned_member=member)
        app = m.Application.objects.create(owner=owner, case=case, kind="petition", status="accepted",
                                           current_version=1, questionnaire=q, submitted_at=timezone.now())
        revision = m.AnswerRevision.objects.create(application=app, number=1, actor=owner, questionnaire=q,
                                                   answers={"grounds": list(grounds)})
        m.Submission.objects.create(application=app, revision=revision, actor=owner, idempotency_key=f"stat-{prefix}-{i}")


def test_counts_and_suppression(granted_roles, client, people):
    make_cases(people, 5, member=people["member"], grounds=("abandonment", "infidelity"))
    make_cases(people, 2, member=None, grounds=("desertion",), prefix="T")  # legacy code reads as abandonment
    data = get(granted_roles, client, people["member"], f"/api/statistics/summary/?year={YEAR}").json()
    assert data["year"] == YEAR and YEAR in data["years"] and data["threshold"] == 5
    members = {row["id"]: row for row in data["cases_per_member"]}
    mine = members[str(people["member"].pk)]
    assert set(mine) == {"id", "name", "count", "suppressed"} and (mine["count"], mine["suppressed"]) == (5, False)
    assert members[str(people["president"].pk)]["count"] is None and members[str(people["president"].pk)]["suppressed"]
    grounds = {row["code"]: row for row in data["cases_by_ground"]}
    assert grounds["abandonment"]["count"] == 7 and grounds["infidelity"]["count"] == 5
    assert grounds["abuse"] == {"code": "abuse", "count": None, "suppressed": True}
    assert "desertion" not in grounds


def test_no_applicant_rows_or_links(granted_roles, client, people):
    make_cases(people, 5, member=people["member"])
    text = get(granted_roles, client, people["secretary"]).content.decode()
    assert "@example.test" not in text and "S-00" not in text and "/api/" not in text


def test_bad_year_is_refused(granted_roles, client, people):
    assert get(granted_roles, client, people["member"], "/api/statistics/summary/?year=abc").status_code == 422


def test_council_only(granted_roles, client, people):
    assert get(granted_roles, client, people["applicant"]).status_code == 403
    client.logout()
    assert get(granted_roles, client, None).status_code == 401


def test_a_single_hidden_cell_cannot_be_worked_out_by_subtraction(granted_roles, client, people):
    """Threshold confirmed at 5 (#170). The year's case total is knowable, so one
    hidden member cell would equal total minus the visible cells; a second cell
    is hidden with it, and no total is published."""
    make_cases(people, 6, member=people["member"], prefix="A")
    make_cases(people, 5, member=people["president"], prefix="B")
    make_cases(people, 2, member=people["secretary"], prefix="C")
    data = get(granted_roles, client, people["secretary"], f"/api/statistics/summary/?year={YEAR}").json()
    assert "total" not in data
    cells = {row["id"]: row for row in data["cases_per_member"]}
    hidden = [row for row in cells.values() if row["suppressed"]]
    assert len(hidden) >= 2 and all(row["count"] is None for row in hidden)
    assert cells[str(people["secretary"].pk)]["suppressed"]
    assert cells[str(people["president"].pk)]["suppressed"]  # smallest visible cell hidden with it
    assert cells[str(people["member"].pk)]["count"] == 6
    grounds = [row for row in data["cases_by_ground"] if row["suppressed"]]
    assert len(grounds) != 1
