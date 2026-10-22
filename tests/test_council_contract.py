from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
import json
import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.management import call_command
from tribunal.models import Account, AgendaItem, AgendaTransferEvent, Notification, Party, ReportQuestion, ReportRequest
from tribunal.services.applications import submit_application, review_application, save_answers
from tribunal.services.council import (
    assign_case, create_session, place_agenda, record_attendance, hear_case,
    save_hearing_outcome, close_session, transfer_agenda_item, update_session,
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


def test_session_workspace_projects_saved_header_and_assignment_facts(client, filed, people):
    app = filed
    Party.objects.create(case=app.case, slot="B", name="Mary Smith")
    starts_at = datetime(2030, 1, 2, 10, 0, tzinfo=ZoneInfo("America/Los_Angeles"))
    session = create_session(
        people["admin"],
        date(2030, 1, 2),
        starts_at=starts_at,
        presiding_member=people["president"],
        location="St. George Coptic Orthodox Church, Bellflower, California",
    )
    place_agenda(people["admin"], session.pk, app.case_id, part=1)
    login(client, people["secretary"])

    data = client.get(f"/api/sessions/{session.pk}/agenda/").json()
    assert data["session"] == {
        **data["session"],
        "reference": "CS20300102",
        "starts_at": starts_at.isoformat(),
        "presiding_member_id": str(people["president"].pk),
        "presiding_member_name": "president Test",
        "location": "St. George Coptic Orthodox Church, Bellflower, California",
    }
    row = data["items"][0]
    assert row["applicant_name"] == "John Smith"
    assert row["respondent_name"] == "Mary Smith"
    assert row["applicant_gender"] == "M"
    assert row["respondent_gender"] is None
    assert row["reason"] == "infidelity"
    assert row["married_years"] == 19
    assert row["submitted_at"] == app.submitted_at.isoformat()
    assert row["assignment_status"] == "unassigned"
    assert row["previous_recommendation"] is None


def test_case_listing_exposes_party_names_for_session_placement_choices(client, filed, people):
    Party.objects.create(case=filed.case, slot="B", name="Mary Smith")
    login(client, people["secretary"])
    row = next(row for row in client.get("/api/cases/").json()["items"] if row["id"] == str(filed.case_id))
    assert row["party_names"] == ["John Smith", "Mary Smith"]
    assert "applicant_gender" in row and "respondent_gender" in row
    assert row["respondent_gender"] is None
    assert {"applicant_name", "respondent_name", "reason", "closed_at"} <= row.keys()


def test_session_agenda_keeps_gender_pills_when_a_party_uses_its_linked_account_person(client, filed, people):
    party = Party.objects.get(case=filed.case, account=filed.owner)
    party.person = None
    party.save(update_fields=["person"])
    session = create_session(people["admin"], date(2030, 1, 2))
    place_agenda(people["admin"], session.pk, filed.case_id, part=1)
    login(client, people["secretary"])

    row = client.get(f"/api/sessions/{session.pk}/agenda/").json()["items"][0]
    assert row["applicant_gender"] == filed.owner.person.gender == "M"


def test_session_workspace_exposes_the_last_recorded_hearing_recommendation(client, hearing, filed, people):
    save_hearing_outcome(people["member"], hearing.pk, "Private notes", "Proceed with reconciliation")
    following = create_session(people["admin"], date(2030, 1, 9))
    place_agenda(people["member"], following.pk, filed.case_id, part=2)
    login(client, people["secretary"])

    row = client.get(f"/api/sessions/{following.pk}/agenda/").json()["items"][0]
    assert row["previous_recommendation"] == "Proceed with reconciliation"


def test_session_create_api_persists_workspace_metadata(client, people):
    login(client, people["admin"])
    starts_at = "2030-01-02T10:00:00-08:00"
    response = client.post(
        "/api/sessions/",
        data=json.dumps({
            "date": "2030-01-02",
            "starts_at": starts_at,
            "presiding_member_id": str(people["president"].pk),
            "location": "St. George Coptic Orthodox Church, Bellflower, California",
        }),
        content_type="application/json",
    )
    assert response.status_code == 201
    assert response.json()["state"] == "draft"
    assert response.json()["can_activate"] is True
    assert response.json() == {
        **response.json(),
        "reference": "CS20300102",
        "starts_at": starts_at,
        "presiding_member_id": str(people["president"].pk),
        "presiding_member_name": "president Test",
        "location": "St. George Coptic Orthodox Church, Bellflower, California",
    }


def test_session_agenda_hides_returned_private_correction(client, filed, people):
    app = filed
    review_application(people["secretary"], app.pk, "reject", "Correct the filing.")
    visible = app.revisions.get(number=app.current_version).answers
    save_answers(app.owner, app.pk, {**visible, "grounds": ["PRIVATE CORRECTION"]}, app.current_version)
    session = create_session(people["admin"], date(2030, 1, 2))
    place_agenda(people["admin"], session.pk, app.case_id, part=1)
    login(client, people["secretary"])

    row = client.get(f"/api/sessions/{session.pk}/agenda/").json()["items"][0]
    assert row["reason"] == "infidelity"
    assert "PRIVATE CORRECTION" not in row["reason"]


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
    completed = client.get(f"/api/cases/{app.case_id}/reports/").json()["items"][0]
    assert completed["completed_by"] == "admin Test"
    assert completed["intake_by"] == "admin Test"
    assert data["sent_at"] and data["created_at"] and data["parent_report_id"] is None


def test_report_template_draft_can_target_both_spouses(client, filed, people):
    second_party = Party.objects.create(case=filed.case, slot="B", name="Mary Smith")
    login(client, people["admin"])
    response = client.post(
        f"/api/cases/{filed.case_id}/requests/",
        {
            "proceeding_id": str(filed.proceeding_id),
            "party_ids": [str(filed.party_id), str(second_party.pk)],
            "kind": "interview",
            "title": "Pre-interview draft",
            "questions": [],
            "language": "en",
        },
        content_type="application/json",
    )
    assert response.status_code == 201
    rows = response.json()["items"]
    created = ReportRequest.objects.filter(pk__in=[row["id"] for row in rows])
    assert {str(row.subject_id) for row in created} == {str(filed.party_id), str(second_party.pk)}
    assert created.count() == 2 and all(row.state == "draft" for row in created)


def test_seeded_question_bank_has_versioned_arabic_wording(client, people):
    call_command("seed_reference", verbosity=0)
    question = ReportQuestion.objects.get(code="OPEN-01", version=2)
    assert question.wording_ar and question.wording_ar != question.wording_en
    login(client, people["admin"])
    row = next(item for item in client.get("/api/report-questions/").json()["items"] if item["code"] == "OPEN-01" and item["version"] == 2)
    assert row["wording_ar"] == question.wording_ar and row["category_ar"] == "الأسئلة الأساسية"


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


def test_d12_decision_projection_retains_issued_decree_and_release_history(client, filed, people):
    from tribunal.models import Attachment, FileVersion, FileTechnicalEvent
    from tribunal.services.decisions import attest_signature, issue_decree, release_decree
    decision = record_decision(people["admin"], filed.proceeding_id, "diss-applicant", "Grounds", {str(filed.party_id): "certificate"})
    approve_decision(people["president"], decision.pk)
    login(client, people["secretary"])
    url = f"/api/proceedings/{filed.proceeding_id}/decision/"
    assert client.get(url).json()["items"][0]["decree"] is None
    attachment = Attachment.objects.create(case=filed.case, proceeding=filed.proceeding, category="DEC", visibility="council")
    file = FileVersion.objects.create(attachment=attachment, number=1, object_key="test/signed.pdf",
        original_name="signed.pdf", display_name="signed.pdf", mime_type="application/pdf",
        byte_count=5, sha256="d" * 64, actor=people["admin"])
    FileTechnicalEvent.objects.create(file=file, task="scan", result="clean")
    attest_signature(people["president"], file.pk, people["president"].pk, "signed_scan", {"confirmed_signed": True})
    decree = issue_decree(people["admin"], decision.pk, file.pk, people["president"].pk)
    release_decree(people["secretary"], decree.pk, filed.party_id)
    release_decree(people["secretary"], decree.pk, filed.party_id, "withdraw")
    result = client.get(url).json()["items"][0]["decree"]
    assert result["id"] == str(decree.pk) and result["reference"] == decree.reference
    assert result["signed_file_id"] == str(file.pk) and result["issued_at"]
    assert result["signer_id"] == str(people["president"].pk)
    assert [row["action"] for row in result["releases"]] == ["release", "withdraw"]
    login(client, filed.owner)
    assert client.get(url).status_code == 403


def test_d13_scan_status_requires_source_access_without_releasing_bytes(client, filed, people):
    from tribunal.models import FileTechnicalEvent
    from tribunal.services.applications import save_answers
    from tribunal.services.files import upload
    from django.core.files.uploadedfile import SimpleUploadedFile
    file = filed.attachments.get(category="MC").versions.first()
    url = f"/api/files/{file.pk}/status/"
    login(client, people["secretary"])
    for state in ["pending", "rejected", "clean"]:
        FileTechnicalEvent.objects.create(file=file, task="scan", result=state)
        assert client.get(url).json() == {"id": str(file.pk), "scan_state": state, "can_download": state == "clean"}
    review_application(people["admin"], filed.pk, "reject", "Replace certificate")
    with pytest.MonkeyPatch.context() as monkeypatch:
        from django.conf import settings
        monkeypatch.setattr(settings, "CTM_SCAN_REQUIRED", False)
        pending = upload(filed.owner, SimpleUploadedFile("pending.pdf", b"%PDF-private"), "MC",
                         app_id=filed.pk, attachment_id=file.attachment_id)
    assert client.get(f"/api/files/{pending.pk}/status/").status_code in {403, 404}
    login(client, filed.owner)
    assert client.get(url).status_code == 403


def test_d15_appeal_supplements_disposition_and_eligible_hearings(client, hearing, filed, people):
    from tribunal.services.applications import start_application, save_answers, waive_fee
    from tribunal.services.decisions import withdraw_application, add_appeal_information, decide_appeal
    withdraw_application(filed.owner, filed.pk)
    appeal = start_application(filed.owner, filed.case_id, "appeal")
    save_answers(filed.owner, appeal.pk, {"statement": "Appeal", "new_information": "Evidence"}, 0)
    waive_fee(people["admin"], appeal.pk)
    submit_application(filed.owner, appeal.pk, "d15-appeal", {"accepted": True, "name": "John Smith"})
    supplement = add_appeal_information(filed.owner, appeal.pk, "Additional facts")
    session = create_session(people["admin"], date(2030, 1, 9))
    item = place_agenda(people["member"], session.pk, filed.case_id)
    record_attendance(people["admin"], session.pk, people["member"].pk, True)
    appeal_hearing = hear_case(people["member"], item.pk)
    url = f"/api/applications/{appeal.pk}/"
    login(client, people["member"])
    data = client.get(url).json()
    assert data["supplements"][0]["id"] == str(supplement.pk)
    assert data["supplements"][0]["text"] == "Additional facts"
    assert data["disposition"] is None and data["can_record_result"]
    assert {"id": str(appeal_hearing.pk), "session_date": "2030-01-09"} in data["eligible_hearings"]
    login(client, people["president"])
    assert not client.get(url).json()["can_record_result"]
    result = decide_appeal(people["member"], appeal.pk, appeal_hearing.pk, "accept", "Accepted grounds")
    login(client, people["member"])
    data = client.get(url).json()
    assert not data["can_record_result"]
    assert data["disposition"]["reopened_proceeding_id"] == str(result.reopened_proceeding_id)
    assert data["disposition"]["hearing_id"] == str(appeal_hearing.pk)
    login(client, filed.owner)
    data = client.get(url).json()
    assert "eligible_hearings" not in data and "can_record_result" not in data
    assert data["supplements"][0]["id"] == str(supplement.pk)
    assert data["supplements"][0]["text"] == "Additional facts"
    assert not data["can_supplement"]


def test_d16_assessment_release_metadata_omits_private_contents(client, filed, people):
    from tribunal.models import MedicalRelease, QuestionnaireVersion
    request = create_request(people["admin"], filed.proceeding_id, filed.party_id, "medical", "Assessment", [])
    url = f"/api/cases/{filed.case_id}/requests/"
    login(client, people["member"])
    row = client.get(url).json()["items"][0]
    assert row["release_status"] == "none" and row["release_scope"] is None
    file = filed.attachments.first().versions.first()
    MedicalRelease.objects.create(request=request, subject=filed.owner,
        declaration=QuestionnaireVersion.objects.get(purpose="medical_release", published=True),
        signature=file, scope={"council": False, "private_note": "PRIVATE CONSENT TEXT"})
    row = client.get(url).json()["items"][0]
    assert row["release_status"] == "out_of_scope"
    assert row["release_scope"] == {"council": False}
    MedicalRelease.objects.create(request=request, subject=filed.owner,
        declaration=QuestionnaireVersion.objects.get(purpose="medical_release", published=True),
        signature=file, scope={"council": True, "private_note": "PRIVATE CONSENT TEXT"})
    row = client.get(url).json()["items"][0]
    assert row["release_status"] == "signed" and row["release_scope"] == {"council": True}
    assert "PRIVATE CONSENT TEXT" not in str(row) and "signature" not in row


def test_d17_note_authorship_editability_and_finding_revisions(client, hearing, filed, people):
    from tribunal.services.council import save_note, save_finding
    note = save_note(people["member"], filed.proceeding_id, "First observation")
    save_note(people["member"], filed.proceeding_id, "Updated observation", note.pk)
    save_finding(people["member"], filed.proceeding_id, "fact-a", {"value": "first"}, [{"note_id": str(note.pk)}])
    save_finding(people["member"], filed.proceeding_id, "fact-a", {"value": "second"})
    login(client, people["member"])
    notes_url = f"/api/proceedings/{filed.proceeding_id}/notes/"
    rows = client.get(notes_url).json()["items"]
    assert [row["version"] for row in rows] == [1, 2]
    assert all(row["author_id"] == str(people["member"].pk) and row["timestamp"] for row in rows)
    assert [row["can_edit"] for row in rows] == [False, True]
    login(client, people["admin"])
    assert not any(row["can_edit"] for row in client.get(notes_url).json()["items"])
    findings_url = f"/api/proceedings/{filed.proceeding_id}/findings/"
    rows = client.get(findings_url).json()["items"]
    assert [row["version"] for row in rows] == [1, 2]
    assert rows[0]["sources"] == [{"note_id": str(note.pk)}]
    login(client, filed.owner)
    assert client.get(notes_url).status_code == 403
    assert client.get(findings_url).status_code == 403


def test_d18_template_projection_publication_and_retirement(client, people):
    from tribunal.services.configuration import create_template
    question = ReportQuestion.objects.create(code="D18", version=1, category="test", wording_en="Question", wording_ar="سؤال")
    personal = create_template(people["member"], "Personal", [question.code])
    login(client, people["member"])
    row = client.get("/api/templates/").json()["items"][0]
    assert row["questions"] == [{"code": "D18", "version": 1}]
    assert row["owner_id"] == str(people["member"].pk) and row["can_retire"] and not row["can_publish"]
    assert client.post(f"/api/templates/{personal.pk}/publish/").status_code == 403
    login(client, people["president"])
    assert client.get("/api/templates/").json()["items"] == []
    assert client.post(f"/api/templates/{personal.pk}/retire/").status_code == 403
    login(client, people["secretary"])
    result = client.post(f"/api/templates/{personal.pk}/publish/")
    assert result.status_code == 201
    shared = result.json()
    assert shared["shared"] and shared["owner_id"] is None and shared["questions"] == row["questions"]
    login(client, people["member"])
    assert client.post(f"/api/templates/{shared['id']}/retire/").status_code == 403
    assert client.post(f"/api/templates/{personal.pk}/retire/").json()["retired"]
    login(client, people["admin"])
    assert client.post(f"/api/templates/{shared['id']}/retire/").json()["retired"]


@pytest.mark.parametrize("parent_kind", ["medical", "psychological"])
def test_assessment_parent_cannot_be_used_for_ordinary_followup(filed, people, parent_kind):
    from tribunal.models import Report
    assessment = create_request(people["admin"], filed.proceeding_id, filed.party_id, parent_kind, "Assessment", [])
    parent = Report.objects.create(request=assessment, author=filed.owner)
    for kind in ["intake", "interview", "external_priest"]:
        with pytest.raises(ValidationError, match="Assessment"):
            create_request(people["admin"], filed.proceeding_id, filed.party_id, kind, "Follow-up", [], parent_id=parent.pk)
    followup = create_request(people["admin"], filed.proceeding_id, filed.party_id, parent_kind, "Assessment follow-up", [], parent_id=parent.pk)
    assert followup.parent_report_id == parent.pk


def test_f20_first_hearing_update_can_wait_for_selected_session_and_revision_never_resends(client, hearing, filed, people):
    from tribunal.models import Message, Outbox, HearingOutcome
    from django.utils import timezone
    login(client, people["member"])
    response = client.post(f"/api/hearings/{hearing.pk}/outcome/", data={"internal_text": "Internal",
        "recommendations": "Recommendation", "applicant_message": "Private update",
        "email_timing": "after_session", "session_id": str(hearing.agenda.session_id)}, content_type="application/json")
    assert response.status_code == 201
    message = Message.objects.get(case=filed.case)
    assert message.email_timing == "after_session" and message.session_id == hearing.agenda.session_id
    jobs = Outbox.objects.filter(kind="message_session", case=filed.case)
    assert jobs.count() == 1 and jobs.get().due_at > timezone.now()
    # Timing fields on a revision cannot create/reschedule/resend a message.
    assert client.post(f"/api/hearings/{hearing.pk}/outcome/", data={"internal_text": "Revised",
        "email_timing": "immediate"}, content_type="application/json").status_code == 201
    assert HearingOutcome.objects.filter(hearing=hearing).count() == 2
    assert Message.objects.filter(case=filed.case).count() == 1 and jobs.count() == 1
    close_session(people["admin"], hearing.agenda.session_id)
    assert jobs.get().due_at <= timezone.now() and jobs.get().delivered_at is None


def test_f20_invalid_first_send_timing_rolls_back_outcome_and_message(hearing, filed, people):
    from tribunal.models import HearingOutcome, Message, CouncilSession
    with pytest.raises(ValidationError):
        save_hearing_outcome(people["member"], hearing.pk, "Internal", "Recommendation", email_timing="unsupported")
    assert not HearingOutcome.objects.filter(hearing=hearing).exists() and not Message.objects.filter(case=filed.case).exists()
    closed = create_session(people["admin"], date(2030, 1, 9))
    close_session(people["admin"], closed.pk)
    with pytest.raises(CouncilSession.DoesNotExist):
        save_hearing_outcome(people["member"], hearing.pk, "Internal", "Recommendation", email_timing="after_session", session_id=closed.pk)
    assert not HearingOutcome.objects.filter(hearing=hearing).exists()


@pytest.mark.django_db(transaction=True)
def test_f20_concurrent_outcome_revision_does_not_repeat_first_message(hearing, filed, people):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    from django.db import connection, connections, transaction
    from tribunal.services.common import lock_key
    from tribunal.models import Message, HearingOutcome, Account
    if connection.vendor != "postgresql":
        pytest.skip("PostgreSQL advisory serialization")
    started = Event()

    def revise():
        try:
            actor = Account.objects.get(pk=people["member"].pk)
            started.set()
            return save_hearing_outcome(actor, hearing.pk, "Second", "Second recommendation")
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=1) as pool:
        with transaction.atomic():
            lock_key(f"hearing-outcome:{hearing.pk}")
            future = pool.submit(revise)
            assert started.wait(timeout=5)
            save_hearing_outcome(people["member"], hearing.pk, "First", "First recommendation", email_timing="after_session", session_id=hearing.agenda.session_id)
        future.result(timeout=10)
    assert HearingOutcome.objects.filter(hearing=hearing).count() == 2
    assert Message.objects.filter(case=filed.case).count() == 1
    assert Message.objects.get(case=filed.case).email_timing == "after_session"


def test_active_session_agenda_requires_an_audited_override_to_move(filed, people):
    app = filed
    assign_case(people["admin"], app.case_id, people["member"].pk, people["president"].pk)
    active_session = create_session(people["admin"], date(2030, 2, 2))
    next_session = create_session(people["admin"], date(2030, 2, 9), state="draft")
    source = place_agenda(people["member"], active_session.pk, app.case_id)

    with pytest.raises(ValidationError, match="tied to an in-session agenda"):
        place_agenda(people["member"], next_session.pk, app.case_id)

    destination = transfer_agenda_item(
        people["member"], source.pk, next_session.pk, "The council ran out of time."
    )
    source.refresh_from_db()
    assert source.state == "transferred"
    assert destination.session_id == next_session.pk
    assert destination.carried_from_id == source.pk
    transfer = AgendaTransferEvent.objects.get(destination_item=destination)
    assert transfer.case_id == app.case_id
    assert transfer.reason == "The council ran out of time."


def test_draft_session_agenda_can_move_to_a_later_open_session(filed, people):
    app = filed
    source_session = create_session(people["admin"], date(2030, 2, 2), state="draft")
    target_session = create_session(people["admin"], date(2030, 2, 9), state="draft")
    source = place_agenda(people["member"], source_session.pk, app.case_id)

    destination = transfer_agenda_item(
        people["member"], source.pk, target_session.pk, "Move to the later planned session."
    )

    assert destination.session_id == target_session.pk


def test_session_metadata_can_be_edited_before_a_hearing(filed, people):
    session = create_session(people["admin"], date(2030, 2, 2), location="Original location")
    updated = update_session(
        people["secretary"], session.pk, date(2030, 2, 9),
        starts_at=datetime(2030, 2, 9, 10, 30, tzinfo=ZoneInfo("America/Los_Angeles")),
        presiding_member=people["president"], location="St. Mark Coptic Orthodox Church",
    )
    assert updated.date == date(2030, 2, 9)
    assert updated.presiding_member_id == people["president"].pk
    assert updated.location == "St. Mark Coptic Orthodox Church"


def test_admin_only_account_cannot_be_a_council_voter(filed, people):
    decision = record_decision(people["admin"], filed.proceeding_id, "denied", "Recorded grounds", {})
    with pytest.raises(PermissionDenied):
        cast_vote(people["admin"], decision.pk, "approve")
    recorded = cast_vote(people["admin"], decision.pk, "approve", people["member"].pk)
    assert recorded.member_id == people["member"].pk
    assert recorded.actor_id == people["admin"].pk
