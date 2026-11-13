"""#312 T2: POST /api/lists/<name>/ engine, validation and the cases list.

Every body is checked against docs/implementation/slices/ctm3-312-server-lists/contract/.
All names, numbers and ids are fictional.
"""
import json
from datetime import timedelta
from pathlib import Path

import pytest
from django.db import connection
from django.test import Client
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from tribunal import models as m
from tests.test_core_policy_completion import granted_roles  # noqa: F401  (fixture)

pytestmark = pytest.mark.django_db

CONTRACT = Path(__file__).resolve().parents[1] / "docs/implementation/slices/ctm3-312-server-lists/contract"
BACKEND = "allauth.account.auth_backends.AuthenticationBackend"


def contract(name):
    return json.loads((CONTRACT / f"post-list-{name}.json").read_text(encoding="utf-8"))


def contract_error(name, when):
    return next(row for row in contract(name)["errors"] if row["when"].startswith(when))


def post(client, name, payload):
    return client.post(f"/api/lists/{name}/", data=json.dumps(payload), content_type="application/json")


def login(client, actor):
    client.force_login(actor, backend=BACKEND)


def account(email, first="", last="", role="applicant", gender=""):
    person = m.Person.objects.create(first_name=first, last_name=last, gender=gender)
    return m.Account.objects.create_user(
        email=email, first_name=first, last_name=last, role=role, email_verified=True, person=person)


def make_case(number, names, *, member=None, created_at=None, status="open"):
    case = m.Case.objects.create(number=number, assigned_member=member, status=status,
                                 created_at=created_at or timezone.now(),
                                 closed_at=timezone.now() if status == "closed" else None)
    parties = []
    for slot, (name, who) in zip("ABC", names):
        parties.append(m.Party.objects.create(
            case=case, slot=slot, name=name, account=who, person=who.person if who else None))
    return case, parties


def file_petition(case, party, owner, answers, *, at=None):
    """A submitted petition with one revision and its formal submission (fictional)."""
    at = at or timezone.now()
    app = m.Application.objects.create(owner=owner, case=case, party=party, kind="petition",
                                       status="submitted", current_version=1, submitted_at=at)
    revision = m.AnswerRevision.objects.create(application=app, number=1, answers=answers, actor=owner)
    m.Submission.objects.create(application=app, revision=revision, actor=owner,
                                idempotency_key=f"list-{app.pk}")
    return app


@pytest.fixture
def contract_case(people):
    member = account("demo.member@example.test", "Fr. Demo", "Member", role="member")
    applicant = account("demo.mina@example.test", "Demo Mina", "Applicant", gender="F")
    respondent = account("demo.respondent@example.test", "Demo", "Respondent", gender="M")
    case, (a, b) = make_case("20261020-04", [("Demo Mina Applicant", applicant), ("Demo Respondent", respondent)],
                             member=member)
    file_petition(case, a, applicant, {"grounds": ["abandonment"], "gender": "F"})
    return case, applicant, member


def test_cases_contract_example(client, granted_roles, people, contract_case):
    case, applicant, _ = contract_case
    spec = contract("cases")
    expected = spec["response"]["body"]
    login(client, people["secretary"])
    with granted_roles("ctm_app", session=True):
        response = post(client, "cases", spec["request"]["body"])
    assert response.status_code == spec["response"]["status"]
    data = response.json()
    assert list(data) == list(expected)
    assert list(data["items"][0]) == list(expected["items"][0])
    assert data["total"] == 1 and data["has_more"] is False and data["page"] == 1 and data["size"] == 50
    row = data["items"][0]
    for key in ["number", "status", "display_status", "assigned_member", "applicant_gender", "respondent_gender",
                "applicant_name", "respondent_name", "grounds", "reason", "closed_at", "party_names"]:
        assert row[key] == expected["items"][0][key], key

    applicant_spec = spec["applicant_response"]
    login(client, applicant)
    with granted_roles("ctm_app", session=True):
        response = post(client, "cases", applicant_spec["request_body"])
    assert response.status_code == applicant_spec["status"]
    data = response.json()
    assert list(data) == list(applicant_spec["body"])
    item = data["items"][0]
    assert list(item) == list(applicant_spec["body"]["items"][0])
    assert not set(applicant_spec["forbidden_item_keys"]) & set(item)
    assert item["id"] == str(case.pk) and item["grounds"] == ["abandonment"] and item["reason"] == "abandonment"
    assert data["total"] == 1


COMMON_ERRORS = [
    ("unknown list name", "drafts", {}),
    ("page not an integer", "cases", {"page": 0}),
    ("page not an integer", "cases", {"page": "1"}),
    ("page not an integer", "cases", {"page": True}),
    ("size not an integer", "cases", {"size": 101}),
    ("size not an integer", "cases", {"size": 1.5}),
    ("sort field not allowed", "cases", {"sort": [{"field": "secret", "dir": "asc"}]}),
    ("more than 3 sort entries", "cases", {"sort": [{"field": "number", "dir": "asc"}] * 4}),
    ("more than 3 sort entries", "cases", {"sort": [{"field": "number", "dir": "up"}]}),
    ("q shorter than 2", "cases", {"q": "a"}),
    ("q shorter than 2", "cases", {"q": "x" * 201}),
    ("filter key not allowed", "cases", {"filters": {"nope": 1}}),
    ("unknown top-level body key", "cases", {"offset": 0}),
    ("filters.status not open", "cases", {"filters": {"status": "pending"}}),
    ("filters.ids not a list", "cases", {"filters": {"ids": ["not-a-uuid"]}}),
    ("filters.ground not one of", "cases", {"filters": {"ground": "desertion"}}),
]


def expected_body(entry, payload):
    body = json.loads(json.dumps(entry["body"]))
    if body and "messages" in body:
        sort = (payload.get("sort") or [{}])[0].get("field", "")
        option = next(iter(payload), "")
        nope = next(iter(payload.get("filters") or {}), "")
        body["messages"] = [text.replace("<field>", str(sort)).replace("<key>", nope if "filter" in entry["when"] else option)
                            for text in body["messages"]]
    return body


@pytest.mark.parametrize("when,name,payload", COMMON_ERRORS)
def test_list_common_errors(client, people, when, name, payload):
    entry = contract_error("cases", when)
    login(client, people["secretary"])
    response = post(client, name, payload)
    assert response.status_code == entry["status"], response.content
    assert response.json() == expected_body(entry, payload)


def test_list_common_errors_signed_out_and_method(client, people):
    assert post(client, "cases", {}).json() == contract_error("cases", "not signed in")["body"]
    assert post(client, "cases", {}).status_code == 401
    login(client, people["secretary"])
    response = client.get("/api/lists/cases/")
    assert response.status_code == 405
    assert response.json() == contract_error("cases", "GET or another method")["body"]


def test_list_csrf_html_403(people):
    entry = contract_error("cases", "CSRF header missing")
    assert entry["body"] is None and entry["content_type"] == "text/html"
    for signed_in in [False, True]:
        client = Client(enforce_csrf_checks=True)
        if signed_in:
            login(client, people["secretary"])
        response = post(client, "cases", {"page": 1})
        assert response.status_code == entry["status"]
        assert response["Content-Type"].startswith(entry["content_type"])
        with pytest.raises(ValueError):
            json.loads(response.content)


def test_applicant_council_only_keys_are_403(client, people, contract_case):
    _, applicant, _ = contract_case
    entry = contract_error("cases", "applicant sends filters.mine")
    login(client, applicant)
    for payload in [{"filters": {"mine": True}}, {"filters": {"assigned": "none"}},
                    {"filters": {"ground": "abuse"}}, {"sort": [{"field": "respondent_name", "dir": "asc"}]},
                    {"sort": [{"field": "applicant_name", "dir": "asc"}]}]:
        response = post(client, "cases", payload)
        assert response.status_code == entry["status"], payload
        assert response.json() == entry["body"]


def test_case_search_total_distinct(client, people):
    make_case("20261101-01", [("Demo Mina One", None), ("Demo Mina Two", None)])
    make_case("20261101-02", [("Demo Other", None)])
    login(client, people["secretary"])
    data = post(client, "cases", {"q": "Mina"}).json()
    assert data["total"] == 1 and len(data["items"]) == 1


def test_case_sort_applicant_name_matches_projection(client, people):
    base = timezone.now()
    filer = account("demo.filer@example.test", "Demo", "Filer")
    make_case("20261102-01", [("Demo Charlie", None), ("Demo Zed", None)], created_at=base)
    make_case("20261102-02", [("Demo Alpha", None), ("Demo Yan", None)], created_at=base + timedelta(minutes=1))
    case, (a, b) = make_case("20261102-03", [("Demo Zulu", None), ("Demo Bravo", filer)],
                             created_at=base + timedelta(minutes=2))
    file_petition(case, b, filer, {"grounds": ["faith"]})  # the filer is in slot B
    login(client, people["secretary"])
    for direction in ["asc", "desc"]:
        items = post(client, "cases", {"sort": [{"field": "applicant_name", "dir": direction}]}).json()["items"]
        names = [row["applicant_name"] for row in items]
        assert names == sorted(names, reverse=direction == "desc")
        assert set(names) == {"Demo Charlie", "Demo Alpha", "Demo Bravo"}
    items = post(client, "cases", {"sort": [{"field": "respondent_name", "dir": "asc"}]}).json()["items"]
    names = [row["respondent_name"] for row in items]
    assert names == sorted(names) and set(names) == {"Demo Zed", "Demo Yan", "Demo Zulu"}


def test_case_search_arabic_digits(client, people):
    make_case("20261020-04", [("Demo Mina Applicant", None)])
    make_case("20261020-05", [("Demo Other", None)])
    login(client, people["secretary"])
    for q in ["٢٠٢٦١٠٢٠-٠٤", "۲۰۲۶۱۰۲۰-۰۴", "  20261020-04  "]:
        data = post(client, "cases", {"q": q}).json()
        assert [row["number"] for row in data["items"]] == ["20261020-04"], q
    data = post(client, "cases", {"q": "Miـna"}).json()
    assert data["total"] == 1 and data["items"][0]["applicant_name"] == "Demo Mina Applicant"


def test_case_search_finds_manager_full_name_and_ground_filter(client, people):
    member = account("demo.manager@example.test", "Fr. Demo", "Member", role="member")
    filer = account("demo.g@example.test", "Demo", "Ground")
    old, (a1,) = make_case("20261103-01", [("Demo Legacy", filer)], member=member)
    new, (a2,) = make_case("20261103-02", [("Demo Current", None)])
    other, (a3,) = make_case("20261103-03", [("Demo Abuse", None)])
    file_petition(old, a1, filer, {"grounds": ["desertion"]})
    file_petition(new, a2, filer, {"grounds": ["abandonment"]})
    file_petition(other, a3, filer, {"grounds": ["abuse"]})
    login(client, people["secretary"])
    data = post(client, "cases", {"q": "Fr. Demo Member"}).json()
    assert [row["number"] for row in data["items"]] == ["20261103-01"]
    data = post(client, "cases", {"filters": {"ground": "abandonment"}, "sort": [{"field": "number", "dir": "asc"}]}).json()
    assert [row["number"] for row in data["items"]] == ["20261103-01", "20261103-02"]
    assert data["total"] == 2
    assert post(client, "cases", {"filters": {"ground": "abuse"}}).json()["total"] == 1
    assert post(client, "cases", {"filters": {"ground": "faith"}}).json()["total"] == 0


def test_case_filters_status_mine_assigned_ids(client, people):
    member = people["member"]
    mine, _ = make_case("20261104-01", [("Demo One", None)], member=member)
    free, _ = make_case("20261104-02", [("Demo Two", None)])
    closed, _ = make_case("20261104-03", [("Demo Three", None)], status="closed")
    login(client, member)

    def numbers(filters):
        return sorted(row["number"] for row in post(client, "cases", {"filters": filters}).json()["items"])

    assert numbers({}) == ["20261104-01", "20261104-02", "20261104-03"]
    assert numbers({"status": "open"}) == ["20261104-01", "20261104-02"]
    assert numbers({"status": "closed"}) == ["20261104-03"]
    assert numbers({"mine": True}) == ["20261104-01"]
    assert numbers({"assigned": "none", "status": "open"}) == ["20261104-02"]
    assert numbers({"ids": [str(free.pk), str(closed.pk)]}) == ["20261104-02", "20261104-03"]
    assert post(client, "cases", {"filters": {"mine": False}}).status_code == 422


def test_case_total_excludes_sort_annotations(client, people):
    make_case("20261105-01", [("Demo Count", None), ("Demo Other", None)])
    login(client, people["secretary"])
    with CaptureQueriesContext(connection) as queries:
        data = post(client, "cases", {"sort": [{"field": "applicant_name", "dir": "asc"}]}).json()
    assert data["total"] == 1
    counts = [query["sql"] for query in queries.captured_queries if "COUNT(" in query["sql"].upper()]
    assert counts and not any("list_applicant_id" in sql for sql in counts)
    assert any("list_applicant_id" in query["sql"] for query in queries.captured_queries)


def test_case_page_past_end(client, people):
    for index in range(3):
        make_case(f"20261106-0{index}", [(f"Demo {index}", None)])
    login(client, people["secretary"])
    data = post(client, "cases", {"page": 99, "size": 2}).json()
    assert data == {"items": [], "page": 99, "size": 2, "total": 3, "has_more": False}
    data = post(client, "cases", {"page": 1, "size": 2}).json()
    assert len(data["items"]) == 2 and data["has_more"] is True and data["total"] == 3
    data = post(client, "cases", {"page": 2, "size": 2}).json()
    assert len(data["items"]) == 1 and data["has_more"] is False
