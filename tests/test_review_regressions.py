import os
import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from tribunal.models import Report, FileVersion
from tribunal.services.applications import submit_application, required_documents
from tribunal.services.decisions import (
    withdraw_application,
    record_decision,
    approve_decision,
)
from tribunal.services.files import upload, private_path
from tribunal.services.reports import create_request, send_request, complete_request

pytestmark = pytest.mark.django_db


def test_required_document_rejects_clean_audio(ready_application):
    app = ready_application
    file = app.attachments.get(category="MC").versions.first()
    # Exercise validation of legacy/imported metadata as well as the upload gate.
    newer = FileVersion.objects.create(
        attachment=file.attachment,
        number=2,
        object_key="bad-legacy",
        original_name="audio.mp3",
        display_name="audio.mp3",
        mime_type="audio/mpeg",
        byte_count=5,
        sha256="b" * 64,
    )
    from tribunal.models import FileTechnicalEvent

    FileTechnicalEvent.objects.create(file=newer, task="scan", result="clean")
    with pytest.raises(ValidationError):
        required_documents(app, {"statement": "Statement"})


def test_upload_category_cannot_disguise_media(ready_application):
    with pytest.raises(ValidationError):
        upload(
            ready_application.owner,
            SimpleUploadedFile("audio.mp3", b"ID3" + b"x" * 30),
            "MC",
            app_id=ready_application.pk,
        )


def test_closed_petition_cannot_be_withdrawn(ready_application, people):
    app = ready_application
    submit_application(
        app.owner, app.pk, "closed-withdraw", {"accepted": True, "name": "John Smith"}
    )
    app.refresh_from_db()
    decision = record_decision(
        people["admin"], app.proceeding_id, "denied", "Reason", {}
    )
    approve_decision(people["president"], decision.pk)
    with pytest.raises(ValidationError):
        withdraw_application(app.owner, app.pk)
    app.party.refresh_from_db()
    assert app.party.withdrawn_at is None


def test_applicant_cannot_read_staff_authored_intake(client, ready_application, people):
    app = ready_application
    submit_application(
        app.owner, app.pk, "report-private", {"accepted": True, "name": "John Smith"}
    )
    app.refresh_from_db()
    request = create_request(
        people["admin"],
        app.proceeding_id,
        app.party_id,
        "intake",
        "Internal intake",
        [],
    )
    send_request(people["admin"], request.pk)
    report = complete_request(
        people["admin"], request.pk, {"private": "Staff narrative"}
    )
    client.force_login(
        app.owner, backend="allauth.account.auth_backends.AuthenticationBackend"
    )
    response = client.get(f"/api/cases/{app.case_id}/reports/")
    assert response.status_code == 200
    assert str(report.pk) not in response.content.decode()


def test_original_file_permissions(
    ready_application, django_capture_on_commit_callbacks
):
    with django_capture_on_commit_callbacks(execute=True):
        file = upload(
            ready_application.owner,
            SimpleUploadedFile("document.pdf", b"%PDF-1.7\nsource"),
            "EVD",
            app_id=ready_application.pk,
        )
    path = private_path(file.object_key)
    assert path.read_bytes() == b"%PDF-1.7\nsource"
    if os.name == "posix":
        assert path.stat().st_mode & 0o777 == 0o600
        assert path.parent.stat().st_mode & 0o777 == 0o700
