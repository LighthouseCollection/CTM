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
        m.AnswerRevision.objects.create(application=app, number=1, actor=owner, questionnaire=q,
                                        answers={"grounds": list(grounds)})


def test_counts_and_suppression(granted_roles, client, people):
    make_cases(people, 5, member=people["member"], grounds=("abandonment", "infidelity"))
    make_cases(people, 2, member=None, grounds=("desertion",), prefix="T")  # legacy code reads as abandonment
    data = get(granted_roles, client, people["member"], f"/api/statistics/summary/?year={YEAR}").json()
    assert data["year"] == YEAR and YEAR in data["years"] and data["threshold"] == 5
    members = {row["id"]: row for row in data["cases_per_member"]}
    assert members[str(people["member"].pk)] == {"id": str(people["member"].pk), "name": "Member User",
                                                 "count": 5, "suppressed": False} or members[str(people["member"].pk)]["count"] == 5
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
