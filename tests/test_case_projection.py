import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from tribunal.models import Attachment, FileTechnicalEvent, FileVersion, Party
from tribunal.services.applications import save_answers, submit_application
from tribunal.services.council import assign_case, save_finding

pytestmark = pytest.mark.django_db


def test_case_projection_flags_support_private_message_composition(
    client, ready_application, people
):
    app = ready_application
    submit_application(
        app.owner, app.pk, "projection", {"accepted": True, "name": "John Smith"}
    )
    app.refresh_from_db()
    url = f"/api/cases/{app.case_id}/"
    client.force_login(
        app.owner, backend="allauth.account.auth_backends.AuthenticationBackend"
    )
    own = client.get(url).json()
    assert own["can_message"] is True
    assert own["parties"][0]["is_self"] is True
    assert own["parties"][0]["can_receive"] is True
    assert "email" not in own["parties"][0]
    client.force_login(
        people["member"], backend="allauth.account.auth_backends.AuthenticationBackend"
    )
    assert client.get(url).json()["can_message"] is False
    assign_case(
        people["admin"], app.case_id, people["member"].pk, people["president"].pk
    )
    assigned = client.get(url).json()
    assert assigned["can_message"] is True
    assert assigned["parties"][0]["is_self"] is False


def test_council_case_detail_projects_submitted_spouse_profile_and_photo(
    client, ready_application, people
):
    app = ready_application
    revision = app.revisions.get(number=app.current_version)
    revision.answers = {
        **revision.answers,
        "other_names": "Johnny",
        "birth_country": "Egypt",
        "nationality": "Egyptian",
        "aware_of_application": "Yes",
        "address": {
            "street": "1842 Maple Dr",
            "city": "Bellflower",
            "region": "California",
            "postal": "90706",
            "country": "United States",
        },
        "mobile": "(562) 555-1042",
        "email": "john.smith@example.test",
        "immigration_status": "Citizen",
        "residing_with": "Alone",
        "education": "Bachelor of Business Administration",
        "graduation_year": "2007",
        "occupation": "Registered Nurse",
        "denomination": "Coptic Orthodox",
        "bishop": "H.E. Metropolitan Serapion",
        "diocese": "Los Angeles, Southern California and Hawaii",
        "parish": "St. Mary Coptic Orthodox Church, Bellflower",
        "confessor": "Fr. Abraam Mikhail",
        "spouse_name": "Jessica O'Brien",
        "spouse_aliases": "Jess",
        "spouse_birth_country": "Egypt",
        "spouse_nationality": "Egyptian",
        "spouse_aware_of_application": "Unknown",
        "spouse_address": "88 Park Ave, Anaheim, California, 92801, United States",
        "spouse_mobile": "(714) 555-0142",
        "spouse_email": "jessica.obrien@example.test",
        "spouse_immigration_status": "Citizen",
        "spouse_residing_with": "Family",
        "spouse_education": "B.A. Education",
        "spouse_graduation_year": "2011",
        "spouse_occupation": "Teacher",
        "spouse_denomination": "Coptic Orthodox",
        "spouse_bishop": "H.E. Metropolitan Serapion",
        "spouse_diocese": "Los Angeles, Southern California and Hawaii",
        "spouse_parish": "St. George Coptic Orthodox Church, Bellflower",
        "spouse_confessor": "Fr. Antony Attallah",
        "married_outside_coptic_church": "No",
        "religious_denomination_officiating": "",
        "date_of_marriage_outside_coptic_church": "",
        "church_marriage_date": "2010-06-12",
        "officiating_priest": "Fr. Antony Attallah",
        "church_name": "St. Mark Coptic Orthodox Church",
        "church_location": "Los Angeles, CA",
        "diocese": "Diocese of Los Angeles",
    }
    # Answer revisions are immutable history; save new answers as a new revision.
    save_answers(app.owner, app.pk, revision.answers, app.current_version)
    submit_application(app.owner, app.pk, "case-profile", {"accepted": True, "name": "John Smith"})
    app.refresh_from_db()
    revision.answers = {
        **revision.answers,
        "marital_status": "Separated",
        "separation_date": "2024-11-03",
        "initiated_by": "self",
        "civil_divorce_filed": "Yes",
        "civil_divorce_date": "2025-01-06",
        "court_name": "Los Angeles Superior Court",
        "court_location": "Los Angeles, CA",
        "civil_case_number": "24STFL-09834",
        "civil_divorce_status": "Finalized",
        "restraining_orders": [{
            "filed": "Yes", "date": "2024-11-10", "court": "Los Angeles Superior Court",
            "case_number": "24DVRO-05217", "status": "Active", "name_listed": "John Smith",
        }],
        "reconciliation_attempted": "Yes",
        "previously_applied": "No",
        "children": [{
            "first_name": "Michael",
            "last_name": "O'Brien",
            "dob": "2017-04-08",
            "gender": "M",
            "lives_with": "self",
        }],
    }
    save_answers(app.owner, app.pk, revision.answers, app.current_version)
    app.refresh_from_db()
    spouse = Party.objects.create(case=app.case, slot="B", name="Jessica O'Brien")
    photo_attachment = Attachment.objects.create(
        application=app, owner=app.owner, category="PHOTO"
    )
    photo = FileVersion.objects.create(
        attachment=photo_attachment,
        number=1,
        object_key=f"test/{photo_attachment.pk}/photo.png",
        original_name="photo.png",
        display_name="photo.png",
        mime_type="image/png",
        byte_count=5,
        sha256="b" * 64,
        actor=app.owner,
        scan_state="clean",
    )
    FileTechnicalEvent.objects.create(file=photo, task="scan", result="clean")
    login = lambda actor: client.force_login(actor, backend="allauth.account.auth_backends.AuthenticationBackend")
    login(people["secretary"])

    detail = client.get(f"/api/cases/{app.case_id}/").json()
    parties = detail["parties"]
    applicant = next(row for row in parties if row["id"] == str(app.party_id))
    respondent = next(row for row in parties if row["id"] == str(spouse.pk))
    assert applicant["profile"]["contact"]["address"] == "1842 Maple Dr, Bellflower, California, 90706, United States"
    assert applicant["profile"]["church_affiliation"]["confessor"] == "Fr. Abraam Mikhail"
    assert applicant["photo_url"] == f"/api/files/{photo.pk}/?view=1"
    assert respondent["profile"]["personal"]["other_names"] == "Jess"
    assert respondent["profile"]["career"]["occupation"] == "Teacher"
    assert respondent["profile"]["church_affiliation"]["parish"] == "St. George Coptic Orthodox Church, Bellflower"
    assert detail["marriage"] == {
        "outside_coptic_church": "No",
        "outside_denomination": None,
        "outside_marriage_date": None,
        "church_marriage_date": "2010-06-12",
        "officiating_priest": "Fr. Antony Attallah",
        "church_name": "St. Mark Coptic Orthodox Church",
        "church_location": "Los Angeles, CA",
        "diocese": "Diocese of Los Angeles",
    }
    for row in parties:
        assert row["profile_source"] == {
            "kind": "applicant_submission",
            "application_id": str(app.pk),
            "revision": app.current_version,
            "submitted_at": app.submitted_at.isoformat(),
        }
    assert detail["marriage_source"] == parties[0]["profile_source"]
    assert detail["summary"]["filing_date"] == app.submitted_at.isoformat()
    assert detail["summary"]["sources"]["filing_date"] == detail["marriage_source"]
    assert detail["summary"]["sources"]["reason"] == detail["marriage_source"]
    assert detail["summary"]["children"] == [{
        "name": "Michael O'Brien",
        "date_of_birth": "2017-04-08",
        "gender": "M",
        "lives_with": "self",
    }]
    assert detail["summary"]["sources"]["children"] == detail["marriage_source"]
    assert detail["summary"]["sources"]["last_hearing_date"] is None
    assert detail["separation"]["marital_status"] == "Separated"
    assert detail["separation"]["initiated_by"]["value"] == "self"
    assert detail["separation"]["civil_divorce"]["case_number"] == "24STFL-09834"
    assert detail["separation"]["restraining_orders"][0]["case_number"] == "24DVRO-05217"
    assert detail["separation"]["reconciliation"]["attempted"] == "Yes"
    assert detail["separation"]["source"] == detail["marriage_source"]


def test_council_case_detail_exposes_versioned_council_card_edits_only_to_council(
    client, ready_application, people
):
    """Council changes supplement the applicant record instead of overwriting it."""
    app = ready_application
    submit_application(
        app.owner, app.pk, "council-card-edit", {"accepted": True, "name": "John Smith"}
    )
    app.refresh_from_db()
    save_finding(
        people["admin"],
        app.proceeding_id,
        "case_card.marriage",
        {"church_name": "St. Mark Coptic Orthodox Church"},
    )
    login = lambda actor: client.force_login(actor, backend="allauth.account.auth_backends.AuthenticationBackend")
    login(people["secretary"])
    council = client.get(f"/api/cases/{app.case_id}/").json()
    assert council["council_edits"]["marriage"]["value"] == {
        "church_name": "St. Mark Coptic Orthodox Church"
    }
    assert council["council_edits"]["marriage"]["source"]["kind"] == "council_record"
    login(app.owner)
    assert "council_edits" not in client.get(f"/api/cases/{app.case_id}/").json()


def test_council_case_detail_prefers_the_latest_council_photo_for_each_party(
    client, ready_application, people
):
    app = ready_application
    submit_application(
        app.owner, app.pk, "council-photo", {"accepted": True, "name": "John Smith"}
    )
    app.refresh_from_db()
    client.force_login(people["secretary"], backend="allauth.account.auth_backends.AuthenticationBackend")
    uploaded = client.post(
        "/api/files/",
        {
            "case_id": str(app.case_id),
            "category": "CASE_PHOTO",
            "context": str(app.party_id),
            "visibility": "council",
            "file": SimpleUploadedFile("council-photo.png", b"\x89PNG\r\n\x1a\nsynthetic", content_type="image/png"),
        },
    )
    assert uploaded.status_code == 201, uploaded.content
    detail = client.get(f"/api/cases/{app.case_id}/").json()
    party = next(row for row in detail["parties"] if row["id"] == str(app.party_id))
    assert party["photo_url"] == f"/api/files/{uploaded.json()['id']}/?view=1"


def test_council_display_text_removes_retired_presidential_wording():
    from tribunal.projections import council_display_text

    assert council_display_text("Decision ready for presidential consideration.") == (
        "Decision ready for Metropolitan consideration."
    )


def test_session_display_location_normalizes_legacy_demo_locations():
    from tribunal.projections import session_display_location

    assert session_display_location("St. Mark Coptic Orthodox Church, Los Angeles, California") == (
        "St. George Coptic Orthodox Church, Bellflower, California"
    )
