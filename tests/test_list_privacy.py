"""#312 T2 privacy: applicant case items (SEC-312-1) and the council-visible revision (SEC-312-2).

Both the new POST /api/lists/cases/ and the existing GET /api/cases/ are checked,
because the GET leaked the same fields before the shared helpers existed.
All names are fictional.
"""
import json

import pytest

from tribunal import models as m
from tribunal.services.applications import (
    GROUNDS, review_application, save_answers, start_application, submit_application, submitted_grounds, waive_fee,
)
from tribunal.services.decisions import withdraw_application
from tests.test_core_policy_completion import granted_roles  # noqa: F401  (fixture)
from tests.test_list_contract import account, contract, file_petition, login, make_case, post

pytestmark = pytest.mark.django_db


def get_cases(client):
    return client.get("/api/cases/").json()["items"]


def test_applicant_case_item_has_no_other_party_filing_data(client, granted_roles, people):
    spec = contract("cases")["applicant_response"]
    first = account("demo.a@example.test", "Demo", "Alpha", gender="F")
    second = account("demo.b@example.test", "Demo", "Beta", gender="M")
    third = account("demo.c@example.test", "Demo", "Gamma", gender="F")
    case, (a, b, c) = make_case("20261107-01", [("Demo Alpha Party", first), ("Demo Beta Party", second),
                                                ("Demo Gamma Party", third)])
    file_petition(case, a, first, {"grounds": ["abandonment"], "gender": "F"})
    file_petition(case, b, second, {"grounds": ["abuse"], "gender": "M", "first_name": "Selfentered",
                                    "last_name": "Betaname"})
    forbidden = ["abuse", "Selfentered", "Betaname", "Demo Beta Party", "Demo Gamma Party", "Demo Alpha Party"]
    for who, grounds in [(first, ["abandonment"]), (third, [])]:
        login(client, who)
        with granted_roles("ctm_app", session=True):
            listed = post(client, "cases", spec["request_body"])
            legacy = client.get("/api/cases/")
        assert listed.status_code == 200 and legacy.status_code == 200
        for response in [listed, legacy]:
            (item,) = response.json()["items"]
            assert list(item) == list(spec["body"]["items"][0])
            assert item["grounds"] == grounds
            assert item["reason"] == ("; ".join(grounds) or None)
            text = response.content.decode()
            assert not [word for word in forbidden if word in text], who.email
            assert "gender" not in text and "next_step" not in text


def ready_for(owner, people, grounds, marriage="2010-05-01"):
    """A paid-up petition draft ready to submit, through the real services (fictional answers)."""
    app = start_application(owner)
    save_answers(owner, app.pk, {
        "first_name": "Demo", "last_name": "Filer", "birth_date": "1985-03-14", "gender": "M",
        "marriage_date": marriage, "spouse_birth_date": "1987-04-02", "grounds": grounds,
        "statement": "Fictional statement"}, 0)
    for category in ["MC", "CMC", "CDD", "PHOTO"]:
        attachment = m.Attachment.objects.create(application=app, owner=owner, category=category)
        file = m.FileVersion.objects.create(
            attachment=attachment, number=1, object_key=f"test/{attachment.pk}", original_name="file.pdf",
            display_name="file.pdf", mime_type="image/jpeg" if category == "PHOTO" else "application/pdf",
            byte_count=5, sha256="c" * 64, actor=owner)
        m.FileTechnicalEvent.objects.create(file=file, task="scan", result="clean")
    waive_fee(people["admin"], app.pk)
    app.refresh_from_db()
    return app


def returned_with_private_abuse(owner, people, key, marriage="2010-05-01"):
    app = ready_for(owner, people, ["abandonment"], marriage)
    submit_application(owner, app.pk, f"{key}-1", {"accepted": True, "name": "Demo Filer"})
    app.refresh_from_db()
    review_application(people["admin"], app.pk, "reject", "Correct the filing.")
    app.refresh_from_db()
    formal = app.revisions.get(number=app.current_version)
    save_answers(owner, app.pk, dict(formal.answers, grounds=["abandonment", "abuse"]), app.current_version)
    app.refresh_from_db()
    return app


def assert_parity(app):
    """The SQL rule picks the same revision as council_revision(app), checked per ground code."""
    from tribunal.services.filing_privacy import council_revision, council_revision_answers_q

    app.refresh_from_db()
    revision = council_revision(app)
    # #369: the list page's prefetch path picks the same revision, with no extra query.
    from django.db import connection
    from django.test.utils import CaptureQueriesContext
    loaded = m.Application.objects.prefetch_related(
        "revisions", "submissions__completenessreview_set").get(pk=app.pk)
    with CaptureQueriesContext(connection) as captured:
        assert council_revision(loaded) == revision
    assert not captured.captured_queries
    visible = set(submitted_grounds(revision.answers)) if revision else set()
    for code in sorted(GROUNDS):
        values = [code, "desertion"] if code == "abandonment" else [code]
        matched = m.Application.objects.filter(pk=app.pk).filter(council_revision_answers_q(values)).exists()
        assert matched == (code in visible), (app.status, code)
    return visible


def council_view(client, people, granted_roles, case, ground):
    login(client, people["secretary"])
    with granted_roles("ctm_app", session=True):
        total = post(client, "cases", {"filters": {"ground": ground}}).json()["total"]
        listed = {row["id"]: row for row in post(client, "cases", {"size": 100}).json()["items"]}
        legacy = {row["id"]: row for row in get_cases(client)}
    return total, listed[str(case)], legacy[str(case)]


def test_ground_filter_ignores_private_correction_revision(client, granted_roles, people):
    first = returned_with_private_abuse(people["applicant"], people, "sec-312-2")
    assert first.status == "returned"
    assert assert_parity(first) == {"abandonment"}
    total, listed, legacy = council_view(client, people, granted_roles, first.case_id, "abuse")
    assert total == 0
    assert listed["grounds"] == legacy["grounds"] == ["abandonment"]
    assert listed["reason"] == legacy["reason"] == "abandonment"
    total, _, _ = council_view(client, people, granted_roles, first.case_id, "abandonment")
    assert total == 1

    submit_application(first.owner, first.pk, "sec-312-2-2", expected_version=first.current_version)
    assert assert_parity(first) == {"abandonment", "abuse"}
    total, listed, legacy = council_view(client, people, granted_roles, first.case_id, "abuse")
    assert total == 1
    assert listed["grounds"] == legacy["grounds"] == ["abandonment", "abuse"]

    # SEC-312-2a: a corrected returned filing is withdrawn; its current_version stays private.
    other = account("demo.withdraw@example.test", "Demo", "Withdraw")
    second = returned_with_private_abuse(other, people, "sec-312-2a", "2012-08-09")
    assert assert_parity(second) == {"abandonment"}
    withdraw_application(other, second.pk)
    second.refresh_from_db()
    assert second.status == "withdrawn"
    assert assert_parity(second) == {"abandonment"}
    total, listed, legacy = council_view(client, people, granted_roles, second.case_id, "abuse")
    assert total == 1  # only the resubmitted first filing
    assert listed["grounds"] == legacy["grounds"] == ["abandonment"]
    assert listed["reason"] == legacy["reason"] == "abandonment"
    login(client, people["secretary"])
    ids = [row["id"] for row in post(client, "cases", {"filters": {"ground": "abuse"}}).json()["items"]]
    assert ids == [str(first.case_id)]


def test_parity_without_any_submission(people):
    owner = account("demo.draft@example.test", "Demo", "Draft")
    case, (a,) = make_case("20261108-01", [("Demo Draft", owner)])
    app = m.Application.objects.create(owner=owner, case=case, party=a, kind="petition", current_version=1)
    m.AnswerRevision.objects.create(application=app, number=1, answers={"grounds": ["faith"]}, actor=owner)
    assert assert_parity(app) == {"faith"}  # visible by the same rule; never-submitted filings are not listed
    legacy = file_petition(case, a, owner, {"reason": "abuse"})
    assert assert_parity(legacy) == {"abuse"}
    empty = file_petition(case, a, owner, {"grounds": [], "reason": ["faith"]})
    assert assert_parity(empty) == {"faith"}


FILING_TABLES = ("tribunal_answerrevision", "tribunal_submission", "tribunal_completenessreview")


def filing_queries(client, granted_roles):
    """Queries on the filing tables for one page of cases, through both list routes."""
    from django.db import connection
    from django.test.utils import CaptureQueriesContext

    counts = []
    with granted_roles("ctm_app", session=True):
        for fetch in [lambda: post(client, "cases", {"size": 100}), lambda: client.get("/api/cases/")]:
            with CaptureQueriesContext(connection) as captured:
                response = fetch()
            assert response.status_code == 200
            counts.append(sum(any(table in query["sql"] for table in FILING_TABLES)
                              for query in captured.captured_queries))
    return counts, response.json()["items"]


def test_case_page_reads_filings_in_constant_queries(client, granted_roles, people):
    """#369 Speed budget: council_revision uses the page's prefetch, never queries per row,
    and still hides the private correction of a returned filing (SEC-312-2)."""
    returned = returned_with_private_abuse(people["applicant"], people, "perf-369")
    for index in range(2):
        owner = account(f"demo.small{index}@example.test", "Demo", f"Small{index}")
        case, (party,) = make_case(f"20200101-{index:02d}", [(f"Demo Small {index}", owner)])
        file_petition(case, party, owner, {"grounds": ["abuse"]})
    login(client, people["secretary"])
    small, before = filing_queries(client, granted_roles)
    for index in range(2, 8):
        owner = account(f"demo.big{index}@example.test", "Demo", f"Big{index}")
        case, (party,) = make_case(f"20200101-{index:02d}", [(f"Demo Big {index}", owner)])
        file_petition(case, party, owner, {"grounds": ["faith"]})
    other = account("demo.perf.returned@example.test", "Demo", "Returned")
    second = returned_with_private_abuse(other, people, "perf-369-b", "2012-08-09")
    big, items = filing_queries(client, granted_roles)
    assert len(items) == len(before) + 7
    assert big == small, (small, big)
    rows = {row["id"]: row for row in items}
    for app in [returned, second]:
        assert rows[str(app.case_id)]["grounds"] == ["abandonment"]
