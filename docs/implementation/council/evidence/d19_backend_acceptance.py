"""Council D19 and C-02 acceptance against backend #7 (copy into a #7 checkout as tests/test_council_revision_acceptance.py; run pytest --ds=ctm.settings_postgres_test).

Synthetic accounts and an isolated PostgreSQL database; no operational data.
"""
import pytest
from tribunal import models as m
from tribunal.services.council import assign_case
from tribunal.services.decisions import close_case
from tribunal.services.reports import complete_request
from tribunal.services.staff_roles import create_tribunal, grant_assignment_presidency
from tests.test_own_requests import filed, sent, login  # noqa: F401  (fixtures)

pytestmark = pytest.mark.django_db


@pytest.fixture
def assigned(filed, people, settings):
    tribunal = create_tribunal(people["admin"], "TEST", "Test institution", "مؤسسة تجريبية")
    settings.CTM_TRIBUNAL_ID = str(tribunal.pk)
    grant_assignment_presidency(people["admin"], people["admin"].pk, tribunal.pk)
    assign_case(people["admin"], filed.case_id, people["member"].pk, people["admin"].pk)
    return filed


def member_report(app, people):
    row = sent(app, people, "interview")
    return complete_request(people["member"], row.pk, {"text": "Original synthetic answer.", "attendance": ["applicant", "spouse"]},
                            "Original synthetic observation.")


def rows(client, app):
    return {r["id"]: r for r in client.get(f"/api/cases/{app.case_id}/reports/").json()["items"]}


def revise(client, report, answers, observations="", expected=201, version=1):
    response = client.post(f"/api/reports/{report.pk}/revisions/",
                           {"expected_version": version, "answers": answers, "observations": observations},
                           content_type="application/json")
    assert response.status_code == expected, response.content
    return response


def history(client, report):
    response = client.get(f"/api/reports/{report.pk}/revisions/")
    assert response.status_code == 200
    return response.json()["items"]


def test_projection_flags_only_the_assigned_member_author(client, assigned, people):
    report = member_report(assigned, people)
    for role, allowed in [("member", True), ("admin", False), ("secretary", False), ("president", False)]:
        login(client, people[role])
        item = rows(client, assigned)[str(report.pk)]
        assert item["can_revise"] is allowed, role
        assert item["author_id"] == str(people["member"].pk) and item["author"] == "member Test"
        assert item["method"] == "written" and item["submitted_at"]
    login(client, assigned.owner)
    assert str(report.pk) not in rows(client, assigned)  # applicant never sees the interview row


def test_author_revision_appends_version_and_keeps_history(client, assigned, people):
    report = member_report(assigned, people)
    login(client, people["member"])
    before = history(client, report)
    assert [r["version"] for r in before] == [1]
    # Payload exactly as the UI builds it: edited text, structured "files" answer carried unchanged.
    revise(client, report, {"text": "Clarified synthetic answer.", "attendance": ["applicant", "spouse"]}, "Revised observation.")
    after = history(client, report)
    assert [r["version"] for r in after] == [2, 1]
    assert after[0]["answers"] == {"text": "Clarified synthetic answer.", "attendance": ["applicant", "spouse"]}
    assert after[0]["observations"] == "Revised observation." and after[0]["actor"] == "member Test"
    assert after[1]["answers"] == before[0]["answers"] and after[1]["observations"] == "Original synthetic observation."
    item = rows(client, assigned)[str(report.pk)]
    assert item["version"] == 2 and item["answers"]["text"] == "Clarified synthetic answer." and item["can_revise"] is True


def test_non_author_is_refused_with_a_readable_reason(client, assigned, people):
    report = member_report(assigned, people)
    for role in ["admin", "secretary", "president"]:
        login(client, people[role])
        body = revise(client, report, {"text": "Rewrite"}, expected=403).json()
        assert body["error"] == "forbidden" and isinstance(body["detail"], str) and body["detail"]
    login(client, people["member"])
    assert [r["version"] for r in history(client, report)] == [1]


def test_reassignment_withdraws_author_authority(client, assigned, people):
    report = member_report(assigned, people)
    other = m.Account.objects.create_user(email="member2@example.test", first_name="member2", last_name="Test",
                                          role="member", email_verified=True)
    assign_case(people["admin"], assigned.case_id, other.pk, people["admin"].pk)
    login(client, people["member"])
    assert rows(client, assigned)[str(report.pk)]["can_revise"] is False
    assert revise(client, report, {"text": "Late rewrite"}, expected=403).json()["detail"]


def test_closed_case_withdraws_revision(client, assigned, people):
    report = member_report(assigned, people)
    close_case(people["admin"], assigned.case, "synthetic_close")
    login(client, people["member"])
    assert rows(client, assigned)[str(report.pk)]["can_revise"] is False
    response = client.post(f"/api/reports/{report.pk}/revisions/", {"expected_version": 1, "answers": {"text": "After closure"}},
                           content_type="application/json")
    assert response.status_code in {403, 422}, response.content
    assert [r["version"] for r in history(client, report)] == [1]


def test_applicant_authored_report_is_not_revisable(client, assigned, people):
    row = sent(assigned, people, "intake")
    report = complete_request(assigned.owner, row.pk, {"text": "Applicant synthetic response."})
    for role in ["member", "admin"]:
        login(client, people[role])
        assert rows(client, assigned)[str(report.pk)]["can_revise"] is False
        revise(client, report, {"text": "Council rewrite"}, expected=403)


def test_c02_stale_version_is_refused_with_current_version(client, assigned, people):
    """C-02: the council editor reads error/current_version from this exact body."""
    report = member_report(assigned, people)
    login(client, people["member"])
    revise(client, report, {"text": "Tab A", "attendance": ["applicant", "spouse"]})
    body = revise(client, report, {"text": "Tab B (edited from v1)", "attendance": ["applicant", "spouse"]}, expected=409).json()
    assert body == {"error": "version_conflict", "current_version": 2}
    assert [r["version"] for r in history(client, report)] == [2, 1]


def test_c02_exact_retry_after_lost_acknowledgement_is_replayed_not_duplicated(client, assigned, people):
    """C-02: Try again resends the identical request; the server returns the retained revision."""
    report = member_report(assigned, people)
    login(client, people["member"])
    answers = {"text": "Reply lost on the way back.", "attendance": ["applicant", "spouse"]}
    first = revise(client, report, answers, "Obs.").json()
    again = revise(client, report, {"attendance": ["applicant", "spouse"], "text": "Reply lost on the way back."}, "Obs.").json()
    assert again == first and first["version"] == 2  # key order is immaterial (jsonb)
    assert [r["version"] for r in history(client, report)] == [2, 1]
    changed = revise(client, report, {**answers, "text": "Edited after the lost reply."}, "Obs.", expected=409).json()
    assert changed == {"error": "version_conflict", "current_version": 2}


def test_c02_deliberate_save_over_newer_version_binds_to_it(client, assigned, people):
    report = member_report(assigned, people)
    login(client, people["member"])
    revise(client, report, {"text": "Other session", "attendance": ["applicant", "spouse"]})
    saved = revise(client, report, {"text": "Mine, after reviewing v2", "attendance": ["applicant", "spouse"]}, version=2).json()
    assert saved["version"] == 3
    assert [r["answers"]["text"] for r in history(client, report)] == ["Mine, after reviewing v2", "Other session", "Original synthetic answer."]


def test_c02_withdrawn_authority_is_a_403_when_the_version_is_present(client, assigned, people):
    """QA run 2 saw 422 for a real denial only because the editor omitted expected_version."""
    report = member_report(assigned, people)
    other = m.Account.objects.create_user(email="member3@example.test", first_name="member3", last_name="Test",
                                          role="member", email_verified=True)
    assign_case(people["admin"], assigned.case_id, other.pk, people["admin"].pk)
    login(client, people["member"])
    body = revise(client, report, {"text": "Late", "attendance": ["applicant", "spouse"]}, expected=403).json()
    assert body["error"] == "forbidden" and body["detail"]
