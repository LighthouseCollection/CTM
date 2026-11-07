"""#199 / D-0048 backend: structured children in the case summary.

The council's case_card.summary finding keeps first name, last name and date of
birth per child (validated). The council view prefers the latest finding over
the filing, with its source marked; the applicant's submission never changes,
and the applicant keeps seeing their own submitted children.
"""
from datetime import timedelta

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from tribunal import models as m
from tribunal.services.applications import save_answers, submit_application
from tribunal.services.council import save_finding
from tests.test_core_policy_completion import granted_roles  # noqa: F401  (fixture)

pytestmark = pytest.mark.django_db
FILED_CHILD = {"id": "6b0d6a8e-3f0e-4c11-9d39-2f4c2b1a7e01", "first_name": "Mary", "last_name": "Smith",
               "date_of_birth": "2015-03-04", "gender": "F", "lives_with": "Applicant"}


@pytest.fixture
def filed(ready_application):
    app = ready_application
    answers = dict(app.revisions.get(number=app.current_version).answers, children=[FILED_CHILD])
    save_answers(app.owner, app.pk, answers, app.current_version)
    app.refresh_from_db()
    submit_application(app.owner, app.pk, "children-199", {"accepted": True, "name": "John Smith"},
                       expected_version=app.current_version)
    app.refresh_from_db()
    return app


def summary_value(children, reason="Abandonment"):
    return {"reason": reason, "children": children}


def test_finding_keeps_first_last_name_and_date_of_birth(people, filed):
    child = {"first_name": "Mary", "last_name": "Smith", "date_of_birth": "2015-03-04"}
    row = save_finding(people["admin"], filed.proceeding_id, "case_card.summary", summary_value([child]))
    assert row.value["children"] == [child]


@pytest.mark.parametrize("child", [
    {"last_name": "Smith", "date_of_birth": "2015-03-04"},
    {"first_name": " ", "last_name": "Smith", "date_of_birth": "2015-03-04"},
    {"first_name": "Mary", "date_of_birth": "2015-03-04"},
    {"first_name": "Mary", "last_name": "Smith", "date_of_birth": "2015-02-30"},
    {"first_name": "Mary", "last_name": "Smith", "date_of_birth": "next year"},
    {"first_name": "Mary", "last_name": "Smith"},
    {"name": "Mary Smith"},
    "Mary Smith",
])
def test_invalid_children_are_refused(people, filed, child):
    with pytest.raises(ValidationError):
        save_finding(people["admin"], filed.proceeding_id, "case_card.summary", summary_value([child]))
    assert not m.FindingRevision.objects.filter(fact_code="case_card.summary").exists()


def test_future_date_of_birth_is_refused(people, filed):
    tomorrow = (timezone.localdate() + timedelta(days=1)).isoformat()
    with pytest.raises(ValidationError, match="future"):
        save_finding(people["admin"], filed.proceeding_id, "case_card.summary",
                     summary_value([{"first_name": "Mary", "last_name": "Smith", "date_of_birth": tomorrow}]))


def test_children_must_be_a_list(people, filed):
    with pytest.raises(ValidationError):
        save_finding(people["admin"], filed.proceeding_id, "case_card.summary", {"children": "Mary"})


def test_council_view_prefers_the_latest_finding_and_the_filing_is_unchanged(granted_roles, client, people, filed):
    url = f"/api/cases/{filed.case_id}/"
    client.force_login(people["secretary"])
    with granted_roles("ctm_app", session=True):
        before = client.get(url).json()["summary"]
    assert before["children"][0]["first_name"] == "Mary" and before["children"][0]["date_of_birth"] == "2015-03-04"
    assert before["sources"]["children"]["kind"] != "council_record"

    edited = [{"first_name": "Mary", "last_name": "Smith-Hayes", "date_of_birth": "2015-03-04"},
              {"first_name": "Peter", "last_name": "Smith", "date_of_birth": "2018-09-12"}]
    save_finding(people["admin"], filed.proceeding_id, "case_card.summary", summary_value(edited))
    with granted_roles("ctm_app", session=True):
        after = client.get(url).json()["summary"]
    assert [(c["first_name"], c["last_name"], c["date_of_birth"]) for c in after["children"]] == [
        ("Mary", "Smith-Hayes", "2015-03-04"), ("Peter", "Smith", "2018-09-12")]
    assert after["children"][1]["name"] == "Peter Smith"
    assert after["sources"]["children"]["kind"] == "council_record"
    assert filed.submissions.get().revision.answers["children"] == [FILED_CHILD]  # applicant record untouched

    client.force_login(filed.owner)
    with granted_roles("ctm_app", session=True):
        own = client.get(url).json()["summary"]
    assert [c["first_name"] for c in own["children"]] == ["Mary"] and own["children"][0]["last_name"] == "Smith"
