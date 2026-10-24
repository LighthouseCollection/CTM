from types import SimpleNamespace
from unittest.mock import patch
import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.utils import timezone
from tribunal import models as m
from tribunal.services.applications import start_application, save_answers
from tribunal.services.payments import create_checkout, own_pending_checkout, safe_checkout_url
from tribunal.services.communications import send_message, log_call
from tribunal.services.reports import complete_request, create_recording, finalize_recording, review_transcript
from tests.test_own_requests import filed, sent, login, consent

pytestmark = pytest.mark.django_db


def test_own_delete_capability_requires_current_version(client, unpaid_application):
    app = unpaid_application
    login(client, app.owner)
    url = f"/api/applications/{app.pk}/"
    row = client.get(url).json()
    assert row["can_delete_draft"] and not row["can_withdraw"]
    delete = f"/api/applications/{app.pk}/delete-draft/"
    for data in [{}, {"expected_version": 0}]:
        assert client.post(delete, data, content_type="application/json").status_code == 422
    assert client.post(delete, {"expected_version": app.current_version}, content_type="application/json").status_code == 200
    assert not client.get(url).json()["can_delete_draft"]


def test_own_withdraw_capability_and_version(client, filed):
    app = filed
    login(client, app.owner)
    url = f"/api/applications/{app.pk}/"
    assert client.get(url).json()["can_withdraw"]
    target = f"/api/applications/{app.pk}/withdraw/"
    for data in [{}, {"expected_version": 0}]:
        assert client.post(target, data, content_type="application/json").status_code == 422
    app.refresh_from_db()
    assert app.status == "submitted"
    assert client.post(target, {"expected_version": app.current_version}, content_type="application/json").status_code == 200
    assert not client.get(url).json()["can_withdraw"]


def provider_checkout(app, settings):
    settings.STRIPE_SECRET_KEY = "synthetic-unused-provider-key"
    session = SimpleNamespace(id=f"cs_{app.pk.hex}", url="https://checkout.stripe.com/c/synthetic",
        expires_at=int((timezone.now()+timezone.timedelta(hours=1)).timestamp()))
    with patch("tribunal.services.payments.stripe.checkout.Session.create", return_value=session) as provider:
        result = create_checkout(app.owner, app.pk, {"accepted": True, "name": "John Smith"},
            "https://ctm.example.test", expected_version=app.current_version)
    return m.CheckoutIntent.objects.get(pk=result["intent"]), provider


def test_original_checkout_resume_read_is_bound_and_has_no_provider_write(client, unpaid_application, settings):
    app = unpaid_application
    intent, provider = provider_checkout(app, settings)
    assert provider.call_count == 1
    login(client, app.owner)
    with patch("tribunal.services.payments.stripe.checkout.Session.create") as create:
        response = client.get(f"/api/applications/{app.pk}/")
        row = response.json()
    assert create.call_count == 0
    assert response["Cache-Control"] == "private, no-store"
    assert row["can_resume_checkout"] and not row["can_checkout"] and not row["can_delete_draft"]
    bound = row["pending_checkout"]
    assert bound["id"] == str(intent.pk) and bound["version"] == app.current_version
    assert bound["attestation"] == {"accepted": True, "name": "John Smith"}
    assert bound["declaration_en"] == intent.revision.questionnaire.declaration_en
    assert bound["declaration_ar"] == intent.revision.questionnaire.declaration_ar
    history = client.get(f"/api/applications/{app.pk}/payments/").json()
    assert history["checkouts"][0]["id"] == bound["id"]
    assert not own_pending_checkout(app, m.Account.objects.exclude(pk=app.owner_id).first())["can_resume_checkout"]


@pytest.mark.parametrize("change", ["stale", "processing", "expired", "hold", "multiple"])
def test_checkout_resume_denies_changed_or_unresolved_candidates(unpaid_application, settings, change):
    app = unpaid_application
    intent, _ = provider_checkout(app, settings)
    if change == "stale":
        revision = app.revisions.get(number=app.current_version)
        save_answers(app.owner, app.pk, {**revision.answers, "statement": "Changed"}, app.current_version)
        app.refresh_from_db()
    elif change == "processing":
        m.CheckoutIntent.objects.filter(pk=intent.pk).update(state="processing")
    elif change == "expired":
        with patch("tribunal.services.payments.timezone.now", return_value=intent.checkout_expires_at+timezone.timedelta(seconds=1)):
            assert not own_pending_checkout(app, app.owner)["can_resume_checkout"]
        return
    elif change == "hold":
        app.duplicate_hold = True
    else:
        m.CheckoutIntent.objects.create(application=app, revision=intent.revision)
    assert own_pending_checkout(app, app.owner) == {"can_resume_checkout": False, "pending_checkout": None}


@pytest.mark.parametrize("url", ["https://evil.test/", "https://checkout.stripe.com.evil.test/x", "javascript:alert(1)",
    "https://user@checkout.stripe.com/x", "https://checkout.stripe.com:444/x", "https://checkout.stripe.com/\nheader"])
def test_resume_url_requires_exact_provider_origin(url):
    assert safe_checkout_url(url) == ""


def test_council_report_authorship_and_author_only_revision_projection(client, filed, people):
    row = sent(filed, people, "interview")
    report = complete_request(people["admin"], row.pk, {"text": "Recorded"})
    for role, allowed in [("admin", True), ("secretary", False), ("member", False)]:
        login(client, people[role])
        item = client.get(f"/api/cases/{filed.case_id}/reports/").json()["items"][0]
        assert item["author_id"] == str(people["admin"].pk)
        assert item["author"] == "admin Test" and item["method"] == "written"
        assert item["can_revise"] is allowed and item["submitted_at"]
    login(client, filed.owner)
    assert not client.get(f"/api/cases/{filed.case_id}/reports/").json()["items"]


def test_message_rejects_unsafe_and_request_bound_links(filed, people):
    file = filed.attachments.get(category="CMC").versions.first()
    m.FileTechnicalEvent.objects.create(file=file, task="scan", result="pending")
    with pytest.raises(PermissionDenied):
        send_message(filed.owner, filed.case_id, "Link", [filed.party_id], file_ids=[str(file.pk)])
    m.FileTechnicalEvent.objects.create(file=file, task="scan", result="clean")
    assert send_message(filed.owner, filed.case_id, "Link", [filed.party_id], file_ids=[str(file.pk)]).file_links == [str(file.pk)]
    row = sent(filed, people, "medical")
    signature = consent(filed, row)
    with pytest.raises(PermissionDenied):
        send_message(filed.owner, filed.case_id, "No private report", [filed.party_id], file_ids=[str(signature.pk)])
    for value in ["not-a-list", [str(file.pk), str(file.pk)]]:
        with pytest.raises(ValidationError):
            send_message(filed.owner, filed.case_id, "Link", [filed.party_id], file_ids=value)


def recorded(filed, people):
    row = sent(filed, people, "interview")
    report = complete_request(people["admin"], row.pk, {"text": "Recorded"})
    attachment = m.Attachment.objects.create(case=filed.case, proceeding=filed.proceeding,
        category="AUDIO", visibility="council")
    file = m.FileVersion.objects.create(attachment=attachment, number=1, object_key=f"recording/{row.pk}",
        mime_type="audio/mpeg", byte_count=5, sha256="c"*64, actor=people["admin"])
    m.FileTechnicalEvent.objects.create(file=file, task="scan", result="clean")
    recording = create_recording(people["admin"], file.pk, report_id=report.pk, notice_recorded=True)
    return recording, report


def test_recording_requires_literal_notice_and_retained_source(filed, people):
    from django.db import DatabaseError, transaction
    recording, report = recorded(filed, people)
    with pytest.raises(ValidationError):
        create_recording(people["admin"], recording.file_id, report_id=report.pk, notice_recorded="false")
    other = sent(filed, people, "interview")
    other_report = complete_request(people["admin"], other.pk, {"text": "Other"})
    with pytest.raises(DatabaseError), transaction.atomic():
        m.Recording.objects.filter(pk=recording.pk).update(report=other_report)
    run = finalize_recording(people["admin"], recording.pk)
    with pytest.raises(DatabaseError), transaction.atomic():
        m.Recording.objects.filter(pk=recording.pk).update(finalized_at=None)
    assert run.state == "queued"


def test_review_requires_validated_output_exact_latest_version_and_authority(filed, people):
    recording, report = recorded(filed, people)
    run = finalize_recording(people["admin"], recording.pk)
    revision = m.TranscriptRevision.objects.create(recording=recording, run=run, number=1, language="en", text="Synthetic generated output")
    with pytest.raises(ValidationError):
        review_transcript(people["admin"], revision.pk)
    m.ProcessingRun.objects.filter(pk=run.pk).update(state="completed")
    with pytest.raises(PermissionDenied):
        review_transcript(people["member"], revision.pk)
    review = review_transcript(people["admin"], revision.pk)
    assert review_transcript(people["admin"], revision.pk).pk == review.pk
    newer = m.TranscriptRevision.objects.create(recording=recording, run=run, number=2, language="en", text="Synthetic correction")
    with pytest.raises(ValidationError):
        review_transcript(people["admin"], revision.pk)
    assert not m.TranscriptReview.objects.filter(revision=newer).exists()
    assert review_transcript(people["admin"], newer.pk).revision_id == newer.pk


def test_call_validation_does_not_create_invalid_history(filed, people):
    for outcome, notes in [("", ""), ("x"*151, ""), ("Reached", ["invalid"]), ("Reached", "x"*100001)]:
        with pytest.raises(ValidationError):
            log_call(people["admin"], filed.case_id, filed.party_id, timezone.now(), outcome, notes)
    assert not m.CallRecord.objects.exists()
