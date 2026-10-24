import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from tribunal import models as m
from tribunal.services.applications import submit_application
from tribunal.services.decisions import withdraw_application
from tribunal.services.reports import create_request, send_request, complete_request, sign_medical_release
from tribunal.services.request_contracts import request_version, own_request_data
from tribunal.services.files import upload, request_file_listing

pytestmark = pytest.mark.django_db


@pytest.fixture
def filed(ready_application):
    app = ready_application
    submit_application(app.owner, app.pk, "own-requests", {"accepted": True, "name": "John Smith"})
    app.refresh_from_db()
    return app


def sent(app, people, kind="intake"):
    row = create_request(people["admin"], app.proceeding_id, app.party_id, kind, "Requested report", [])
    send_request(people["admin"], row.pk)
    row.refresh_from_db()
    return row


def login(client, actor):
    client.force_login(actor, backend="allauth.account.auth_backends.AuthenticationBackend")


def consent(app, row, category="CONSENT"):
    attachment = m.Attachment.objects.create(case=app.case, proceeding=app.proceeding,
        report_request=row, owner=app.owner, category=category, visibility="medical")
    file = m.FileVersion.objects.create(attachment=attachment, number=1, object_key=f"synthetic-consent-{attachment.pk}",
        original_name="consent.pdf", display_name="consent.pdf", mime_type="application/pdf",
        byte_count=5, sha256="a" * 64, actor=app.owner)
    m.FileTechnicalEvent.objects.create(file=file, task="scan", result="clean")
    return file


def sign(app, row, file, **kwargs):
    data = dict(expected_version=request_version(row),
        declaration_id=m.QuestionnaireVersion.objects.filter(purpose="medical_release").order_by("-number").first().pk, accepted=True)
    data.update(kwargs)
    return sign_medical_release(app.owner, row.pk, file.pk, {"council": True}, **data)


def test_closure_never_publishes_unsent_drafts(client, filed, people):
    row = sent(filed, people)
    draft = create_request(people["admin"], filed.proceeding_id, filed.party_id, "intake", "PRIVATE DRAFT", [])
    withdraw_application(filed.owner, filed.pk)
    login(client, filed.owner)
    response = client.get(f"/api/cases/{filed.case_id}/requests/")
    assert [x["id"] for x in response.json()["items"]] == [str(row.pk)]
    assert b"PRIVATE DRAFT" not in response.content
    assert response.json()["items"][0]["can_respond"] is False
    draft.refresh_from_db()
    assert draft.state == "cancelled" and draft.sent_at is None
    assert client.get(f"/api/requests/{draft.pk}/files/").status_code == 403


def test_own_capability_and_version_http_contract(client, filed, people):
    row = sent(filed, people)
    login(client, filed.owner)
    item = client.get(f"/api/cases/{filed.case_id}/requests/").json()["items"][0]
    assert item["can_respond"] is True and item["can_sign_release"] is False
    assert item["proceeding_id"] == str(filed.proceeding_id)
    url = f"/api/requests/{row.pk}/complete/"
    for version in [None, "stale"]:
        response = client.post(url, {"answers": {"text": "response"}, "expected_version": version}, content_type="application/json")
        assert response.status_code == 422
    response = client.post(url, {"answers": {"text": "response"}, "expected_version": item["request_version"]}, content_type="application/json")
    assert response.status_code == 201
    receipt = response.json()
    assert client.post(url, {"answers": {"text": "response"}, "expected_version": item["request_version"]}, content_type="application/json").json() == receipt
    item = client.get(f"/api/cases/{filed.case_id}/requests/").json()["items"][0]
    assert item["can_respond"] is False and item["response"]["id"] == receipt["id"]


def test_consent_bound_definition_scope_and_replay(filed, people):
    row = sent(filed, people, "medical")
    data = own_request_data(row, filed.owner)
    assert not data["can_respond"] and data["can_sign_release"]
    assert data["release_definition"]["declaration_ar"]
    file = consent(filed, row)
    for kwargs in [{"declaration_id": "wrong"}, {"accepted": "true"}, {"expected_version": "stale"}]:
        with pytest.raises(ValidationError):
            sign(filed, row, file, **kwargs)
    release = sign(filed, row, file)
    assert sign(filed, row, file).pk == release.pk
    assert m.MedicalRelease.objects.filter(request=row).count() == 1
    assert release.scope == {"council": True, "purpose": "medical", "request_id": str(row.pk), "proceeding_id": str(row.proceeding_id)}
    data = own_request_data(row, filed.owner)
    assert data["can_respond"] and not data["can_sign_release"]
    assert data["signed_releases"][0]["declaration_id"] == str(release.declaration_id)
    with pytest.raises(PermissionDenied):
        own_request_data(row, people["member"])


def test_missing_bilingual_definition_disables_consent(filed, people):
    row = sent(filed, people, "psychological")
    # Published definitions are immutable; a newer incomplete version must fail closed.
    m.QuestionnaireVersion.objects.create(purpose="medical_release", number=2, published=True, declaration_en="Synthetic text")
    data = own_request_data(row, filed.owner)
    assert data["release_definition"] is None and not data["can_sign_release"]
    with pytest.raises(ValidationError):
        sign(filed, row, consent(filed, row))


@pytest.mark.parametrize("scope", [{"council": "true"}, {"council": 1}, {"council": True, "external": True}, [], None])
def test_scope_requires_exact_explicit_recipient(filed, people, scope):
    row = sent(filed, people, "medical")
    file = consent(filed, row)
    with pytest.raises(ValidationError):
        sign_medical_release(filed.owner, row.pk, file.pk, scope, accepted=True,
            declaration_id=m.QuestionnaireVersion.objects.get(purpose="medical_release").pk)


def test_consent_cannot_be_report_and_wrong_purpose_cannot_be_signature(filed, people):
    row = sent(filed, people, "medical")
    file = consent(filed, row)
    sign(filed, row, file)
    with pytest.raises(PermissionDenied):
        complete_request(filed.owner, row.pk, {"files": [str(file.pk)]})
    other = sent(filed, people, "medical")
    wrong = consent(filed, other, category="REPORT")
    with pytest.raises(ValidationError):
        sign(filed, other, wrong)


def test_request_files_pending_clean_latest_and_owner_isolation(client, filed, people, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    settings.CTM_SCAN_REQUIRED = True
    settings.CLAMAV_HOST = ""
    row = sent(filed, people, "medical")
    file = upload(filed.owner, SimpleUploadedFile("report.pdf", b"%PDF-1.7 synthetic"), "REPORT",
        request_id=row.pk, expected_request_version=request_version(row))
    login(client, filed.owner)
    url = f"/api/requests/{row.pk}/files/"
    response = client.get(url)
    assert response["Cache-Control"] == "private, no-store"
    item = response.json()["items"][0]
    assert item["purpose"] == "report" and item["scan_state"] == "pending" and "download_url" not in item
    m.FileTechnicalEvent.objects.create(file=file, task="scan", result="clean")
    assert client.get(url).json()["items"][0]["download_url"] == f"/api/files/{file.pk}/"
    login(client, people["member"])
    assert client.get(url).status_code == 403
    with pytest.raises(ValidationError):
        upload(filed.owner, SimpleUploadedFile("report.pdf", b"%PDF-1.7 synthetic"), "REPORT", request_id=row.pk)


@pytest.mark.parametrize("kind", ["interview", "external_priest"])
def test_applicant_cannot_upload_to_staff_or_external_requests(filed, people, kind):
    row = sent(filed, people, kind)
    with pytest.raises(PermissionDenied):
        upload(filed.owner, SimpleUploadedFile("report.pdf", b"%PDF-1.7 synthetic"), "REPORT",
            request_id=row.pk, expected_request_version=request_version(row))


def test_response_validation_safe_scoped_files_and_recovery_after_close(filed, people):
    row = sent(filed, people)
    for answers in [[], "text", {}, {"files": "wrong"}, {"files": ["duplicate", "duplicate"]}]:
        with pytest.raises(ValidationError):
            complete_request(filed.owner, row.pk, answers)
    other = sent(filed, people, "medical")
    file = consent(filed, other)
    with pytest.raises(PermissionDenied):
        complete_request(filed.owner, row.pk, {"files": [str(file.pk)]})
    report = complete_request(filed.owner, row.pk, {"text": "retained"})
    withdraw_application(filed.owner, filed.pk)
    assert complete_request(filed.owner, row.pk, {"text": "retained"}).pk == report.pk
    with pytest.raises(ValidationError):
        complete_request(filed.owner, row.pk, {"text": "changed"})
    assert m.ReportRevision.objects.filter(report=report).count() == 1


def test_send_retry_retains_snapshot_and_notification(filed, people):
    row = sent(filed, people)
    version = request_version(row)
    send_request(people["admin"], row.pk)
    row.refresh_from_db()
    assert request_version(row) == version
    assert m.Notification.objects.filter(recipient=filed.owner, kind="report_requested").count() == 1


def test_council_completion_remains_compatible_without_applicant_fingerprint(client, filed, people):
    row = sent(filed, people, "interview")
    login(client, people["admin"])
    response = client.post(f"/api/requests/{row.pk}/complete/", {"answers": {"text": "Staff entered response"},
        "observations": "Internal"}, content_type="application/json")
    assert response.status_code == 201
    assert m.Report.objects.get(pk=response.json()["id"]).author_id == people["admin"].pk


def test_existing_out_of_scope_release_requires_resolution(filed, people):
    row = sent(filed, people, "medical")
    file = consent(filed, row)
    m.MedicalRelease.objects.create(request=row, subject=filed.owner, signature=file,
        declaration=m.QuestionnaireVersion.objects.get(purpose="medical_release"), scope={"council": False})
    data = own_request_data(row, filed.owner)
    assert data["release_status"] == "out_of_scope" and not data["can_sign_release"] and not data["can_respond"]
    assert data["signed_releases"][0]["scope"] == {"council": False}
    with pytest.raises(ValidationError):
        sign(filed, row, file)


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("operation", ["complete", "sign", "close"])
def test_request_writes_serialize_and_recover(filed, people, operation):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    from django.db import connection, connections, transaction
    if connection.vendor != "postgresql":
        pytest.skip("PostgreSQL request row serialization")
    row = sent(filed, people, "medical" if operation == "sign" else "intake")
    signature = consent(filed, row) if operation == "sign" else None
    started = Event()

    def waiting_write():
        try:
            started.set()
            if operation == "sign":
                return sign(filed, row, signature).pk
            return complete_request(filed.owner, row.pk, {"text": "Retried"}).pk
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=1) as pool:
        with transaction.atomic():
            m.Proceeding.objects.select_for_update().get(pk=filed.proceeding_id)
            future = pool.submit(waiting_write)
            assert started.wait(timeout=5)
            if operation == "close":
                withdraw_application(filed.owner, filed.pk)
            elif operation == "sign":
                first = sign(filed, row, signature).pk
            else:
                first = complete_request(filed.owner, row.pk, {"text": "Retried"}).pk
        if operation == "close":
            with pytest.raises(ValidationError):
                future.result(timeout=10)
            assert not m.Report.objects.filter(request=row).exists()
        else:
            assert future.result(timeout=10) == first
            model = m.MedicalRelease if operation == "sign" else m.Report
            assert model.objects.filter(request=row).count() == 1


def test_required_questions_and_pending_report_file_cannot_complete(filed, people):
    m.ReportQuestion.objects.create(code="REQUIRED", version=1, foundational=True,
        wording_en="Synthetic question", wording_ar="سؤال تجريبي")
    row = sent(filed, people)
    for value in [None, "   ", []]:
        with pytest.raises(ValidationError):
            complete_request(filed.owner, row.pk, {"REQUIRED": value})
    medical = sent(filed, people, "medical")
    signature = consent(filed, medical)
    sign(filed, medical, signature)
    report_file = consent(filed, medical, category="REPORT")
    m.FileTechnicalEvent.objects.create(file=report_file, task="scan", result="pending")
    with pytest.raises(ValidationError):
        complete_request(filed.owner, medical.pk, {"files": [str(report_file.pk)]})
    m.FileTechnicalEvent.objects.create(file=report_file, task="scan", result="clean")
    assert complete_request(filed.owner, medical.pk, {"files": [str(report_file.pk)]}).request_id == medical.pk
