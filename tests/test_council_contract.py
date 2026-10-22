from datetime import date, timedelta
import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from tribunal.models import Account, AgendaItem, Notification, ReportQuestion
from tribunal.services.applications import submit_application, review_application
from tribunal.services.council import (
    assign_case, create_session, place_agenda, record_attendance, hear_case,
    save_hearing_outcome, close_session,
)
from tribunal.services.decisions import record_decision, cast_vote, approve_decision
from tribunal.services.reports import create_request, send_request, complete_request

pytestmark = pytest.mark.django_db


def login(client, actor):
    client.force_login(actor, backend="allauth.account.auth_backends.AuthenticationBackend")


@pytest.fixture
def filed(ready_application):
    app = ready_application
    submit_application(app.owner, app.pk, "council-contract", {"accepted": True, "name": "John Smith"})
    app.refresh_from_db()
    return app


@pytest.fixture
def hearing(filed, people):
    app = filed
    assign_case(people["admin"], app.case_id, people["member"].pk, people["president"].pk)
    session = create_session(people["admin"], date(2030, 1, 2))
    item = place_agenda(people["member"], session.pk, app.case_id)
    record_attendance(people["admin"], session.pk, people["member"].pk, True)
    return hear_case(people["member"], item.pk)


def test_review_queue_has_frozen_manifest_labels_and_authority(client, filed, people):
    app = filed
    login(client, people["secretary"])
    data = client.get("/api/applications/?state=awaiting_review").json()["items"][0]
    assert data["applicant_name"] == "John Smith" and data["can_review"]
    assert data["submitted_at"] and data["submitted_version"] == 1
    assert data["questionnaire"]["id"] == str(app.questionnaire_id)
    assert len(data["manifest"]) == 4 and all(x["scan_state"] == "clean" for x in data["manifest"])
    assert all("sha256" not in row and "object_key" not in row for row in data["manifest"])
    review_application(people["secretary"], app.pk, "reject", "Correct date.")
    data = client.get(f"/api/applications/{app.pk}/").json()
    assert not data["can_review"] and data["reviews"][0]["instructions"] == "Correct date."
    assert client.get("/api/applications/?state=awaiting_review").json()["items"] == []
    login(client, people["member"])
    assert not client.get(f"/api/applications/{app.pk}/").json()["can_review"]
    login(client, app.owner)
    assert client.get("/api/applications/?state=awaiting_review").status_code == 403


def test_assignment_part_one_is_completed_without_carryover(filed, people):
    app = filed
    session = create_session(people["admin"], date(2030, 1, 2))
    following = create_session(people["admin"], session.date + timedelta(days=7))
    item = place_agenda(people["admin"], session.pk, app.case_id, part=1)
    assign_case(people["admin"], app.case_id, people["member"].pk, people["president"].pk)
    close_session(people["admin"], session.pk)
    item.refresh_from_db()
    assert item.state == "assigned" and not following.agenda.exists()


def test_agenda_capabilities_match_presenter_attendance_and_hearing_state(client, filed, people):
    app = filed
    assign_case(people["admin"], app.case_id, people["member"].pk, people["president"].pk)
    session = create_session(people["admin"], date(2030, 1, 2))
    item = place_agenda(people["member"], session.pk, app.case_id)
    login(client, people["member"])
    url = f"/api/sessions/{session.pk}/agenda/"
    data = client.get(url).json()
    assert not data["session"]["can_manage"] and not data["items"][0]["can_present"]
    record_attendance(people["admin"], session.pk, people["member"].pk, True)
    row = client.get(url).json()["items"][0]
    assert row["can_present"] and row["hearing_id"] is None
    assert row["assigned_member_id"] == str(people["member"].pk)
    assert row["party_names"] == ["John Smith"]
    heard = hear_case(people["member"], item.pk)
    row = client.get(url).json()["items"][0]
    assert row["hearing_id"] == str(heard.pk) and not row["can_present"]
    assert row["can_record_outcome"]
    login(client, people["president"])
    assert not client.get(url).json()["items"][0]["can_record_outcome"]
    login(client, people["secretary"])
    assert client.get(url).json()["session"]["can_close"]


def test_hearing_read_keeps_outcome_history_private(client, hearing, filed, people):
    first = save_hearing_outcome(people["member"], hearing.pk, "Internal", "Recommendation")
    save_hearing_outcome(people["member"], hearing.pk, "Revised", "Updated")
    login(client, people["president"])
    data = client.get(f"/api/hearings/{hearing.pk}/").json()
    assert [x["internal_text"] for x in data["outcomes"]] == ["Internal", "Revised"]
    assert data["outcomes"][0]["id"] == str(first.pk)
    assert not data["can_record_outcome"]
    login(client, filed.owner)
    assert client.get(f"/api/hearings/{hearing.pk}/").status_code == 403


def test_case_capabilities_and_active_president_roster(client, filed, people):
    app = filed
    assign_case(people["admin"], app.case_id, people["member"].pk, people["president"].pk)
    login(client, people["member"])
    data = client.get(f"/api/cases/{app.case_id}/").json()
    assert data["can_place_part2"] and not data["can_assign"]
    login(client, app.owner)
    data = client.get(f"/api/cases/{app.case_id}/").json()
    assert not data["can_place_part2"] and not data["can_assign"]
    login(client, people["admin"])
    Account.objects.create_user(email="inactive@example.test", role="member", is_active=False)
    rows = client.get("/api/council/members/").json()["items"]
    assert len(rows) == 4 and all(x["active"] for x in rows)
    assert next(x for x in rows if x["id"] == str(people["president"].pk))["president"]


def test_decision_read_retains_versions_effective_votes_and_approval(client, filed, people):
    app = filed
    first = record_decision(people["admin"], app.proceeding_id, "diss-both", "Grounds", {})
    cast_vote(people["member"], first.pk, "deny")
    cast_vote(people["admin"], first.pk, "approve", people["member"].pk)
    approve_decision(people["president"], first.pk)
    second = record_decision(people["admin"], app.proceeding_id, "deferred", "More inquiry", {})
    login(client, people["member"])
    response = client.get(f"/api/proceedings/{app.proceeding_id}/decision/")
    assert response.status_code == 200
    rows = response.json()["items"]
    assert rows[0]["id"] == str(second.pk) and rows[0]["approval"] is None and not rows[0]["votes"]
    assert rows[1]["votes"][0]["choice"] == "approve" and len(rows[1]["vote_history"]) == 2
    assert rows[1]["approval"]["president_id"] == str(people["president"].pk)
    assert not rows[1]["current"] and not rows[1]["can_vote"]
    login(client, app.owner)
    assert client.get(f"/api/proceedings/{app.proceeding_id}/decision/").status_code == 403


def test_manager_interview_does_not_notify_applicant_or_accept_applicant_completion(client, filed, people):
    app = filed
    request = create_request(people["admin"], app.proceeding_id, app.party_id, "interview", "Interview", [])
    send_request(people["admin"], request.pk)
    assert not Notification.objects.filter(recipient=app.owner, kind="report_requested").exists()
    with pytest.raises(PermissionDenied):
        complete_request(app.owner, request.pk, {"answer": "Not authorized"})
    report = complete_request(people["admin"], request.pk, {"answer": "Recorded"}, "Council observations")
    assert report.author_id == people["admin"].pk
    login(client, people["member"])
    data = client.get(f"/api/cases/{app.case_id}/requests/").json()["items"][0]
    assert data["subject_party_id"] == str(app.party_id) and data["subject_name"] == "John Smith"
    assert data["language"] == "en" and data["author"] == "admin Test"
    assert data["sent_at"] and data["created_at"] and data["parent_report_id"] is None


def test_question_taxonomy_preserves_multiple_groups_and_missing_translation(client, people):
    ReportQuestion.objects.create(code="DEC-01", category="Decision to marry", wording_en="Approved source")
    login(client, people["member"])
    row = client.get("/api/report-questions/").json()["items"][0]
    assert row["category_id"] == "QC05"
    assert {group["id"] for group in row["topic_groups"]} == {"TG02", "TG03"}
    assert row["category_ar"] is None and row["wording_ar"] == ""
    assert all(group["title_ar"] is None for group in row["topic_groups"])


def test_unapproved_arabic_question_cannot_be_sent(filed, people):
    app = filed
    ReportQuestion.objects.create(code="AR-TEST", category="Test", wording_en="English only")
    request = create_request(people["admin"], app.proceeding_id, app.party_id,
                             "intake", "Request", ["AR-TEST"], language="ar")
    with pytest.raises(ValidationError, match="wording is missing"):
        send_request(people["admin"], request.pk)
    request.refresh_from_db()
    assert request.state == "draft" and request.sent_at is None


def test_part_one_assignment_is_not_a_case_hearing(filed, people):
    app = filed
    assign_case(people["admin"], app.case_id, people["member"].pk, people["president"].pk)
    session = create_session(people["admin"], date(2030, 1, 2))
    item = place_agenda(people["admin"], session.pk, app.case_id, part=1)
    record_attendance(people["admin"], session.pk, people["member"].pk, True)
    with pytest.raises(ValidationError):
        hear_case(people["member"], item.pk)
