from unittest.mock import patch
import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from tribunal.models import Account, Attachment, FileVersion, FileTechnicalEvent
from tribunal.services.applications import save_answers, required_documents, submit_application
from tribunal.services.files import upload

pytestmark = pytest.mark.django_db


def login(client, actor):
    client.force_login(actor, backend="allauth.account.auth_backends.AuthenticationBackend")


def test_own_draft_files_include_safe_links_and_requirements(client, ready_application):
    app = ready_application
    login(client, app.owner)
    data = client.get(f"/api/applications/{app.pk}/files/").json()
    assert data["can_upload"] and len(data["items"]) == 4
    assert {x["category"] for x in data["requirements"] if x["required"]} == {"MC", "CMC", "CDD", "PHOTO"}
    assert all(x["scan_state"] == "clean" and x["download_url"] == f"/api/files/{x['id']}/" for x in data["items"])
    assert all("object_key" not in x and "sha256" not in x for x in data["items"])
    assert all(x["label_en"] and x["label_ar"] for x in data["requirements"])


@pytest.mark.parametrize("state", ["pending", "rejected", "unknown"])
def test_latest_pending_file_does_not_fall_back_to_old_clean(client, ready_application, state):
    app = ready_application
    source = app.attachments.get(category="MC").versions.get()
    current = FileVersion.objects.create(
        attachment=source.attachment, number=2, object_key="pending/new.pdf",
        original_name="new.pdf", display_name="new.pdf", mime_type="application/pdf",
        byte_count=5, sha256="b" * 64, actor=app.owner,
    )
    FileTechnicalEvent.objects.create(file=current, task="scan", result=state)
    login(client, app.owner)
    rows = client.get(f"/api/applications/{app.pk}/files/").json()["items"]
    row = next(x for x in rows if x["category"] == "MC")
    assert row["id"] == str(current.pk) and "download_url" not in row
    assert row["scan_state"] == (state if state != "unknown" else "pending")
    assert str(source.pk) not in {x["id"] for x in rows}
    assert not client.get(f"/api/applications/{app.pk}/").json()["can_submit"]


def test_file_listing_denies_others_staff_and_history(client, ready_application, people):
    app = ready_application
    url = f"/api/applications/{app.pk}/files/"
    assert client.get(url).status_code == 401
    outsider = Account.objects.create_user(email="file-outsider@example.test", email_verified=True)
    for actor in [outsider, people["admin"], people["member"]]:
        login(client, actor)
        assert client.get(url).status_code == 403
    login(client, app.owner)
    assert client.get(url + "?history=1").status_code == 403


def test_contextual_order_requirements_and_statement_alternative(client, ready_application):
    app = ready_application
    answers = app.revisions.get(number=1).answers
    orders = [{"id": value, "court": "Court", "number": "1", "status": "active"} for value in ["one", "two"]]
    save_answers(app.owner, app.pk, {**answers, "statement": "", "restraining_orders": orders}, 1)
    login(client, app.owner)
    data = client.get(f"/api/applications/{app.pk}/files/").json()
    assert {x["context"] for x in data["requirements"] if x["category"] == "RO"} == {"one", "two"}
    assert next(x for x in data["requirements"] if x["category"] == "PET")["required"]
    with pytest.raises(ValidationError):
        required_documents(app, {**answers, "restraining_orders": orders})


@pytest.mark.parametrize("orders", [[{"id": ""}], [{"id": "same"}, {"id": "same"}], [None]])
def test_invalid_order_identifiers_do_not_allow_shared_document(ready_application, orders):
    app = ready_application
    answers = app.revisions.get(number=1).answers
    with pytest.raises(ValidationError, match="saved identifier"):
        required_documents(app, {**answers, "restraining_orders": orders})


def test_replacement_cannot_change_saved_context_or_visibility(ready_application):
    app = ready_application
    attachment = app.attachments.get(category="MC")
    source = attachment.versions.get()
    for context, visibility in [("another", "own"), ("", "medical")]:
        with pytest.raises(PermissionDenied):
            upload(app.owner, SimpleUploadedFile("new.pdf", b"%PDF-test"), "MC",
                   app_id=app.pk, attachment_id=attachment.pk, context=context, visibility=visibility)
    assert attachment.versions.count() == 1
    assert attachment.versions.get().pk == source.pk


def test_actual_upload_route_and_same_context_replacement(client, ready_application):
    app = ready_application
    attachment = app.attachments.get(category="MC")
    login(client, app.owner)
    with patch("tribunal.services.files.scan", return_value="pending"):
        response = client.post("/api/files/", {
            "application_id": str(app.pk), "category": "MC", "context": "",
            "visibility": "own", "attachment_id": str(attachment.pk),
            "file": SimpleUploadedFile("new.pdf", b"%PDF-test"),
        })
    assert response.status_code == 201 and response.json()["scan_state"] == "pending"
    assert attachment.versions.count() == 2
    rows = client.get(f"/api/applications/{app.pk}/files/").json()["items"]
    row = next(x for x in rows if x["attachment_id"] == str(attachment.pk))
    assert row["id"] == response.json()["id"] and "download_url" not in row


def test_closed_original_disables_upload(client, ready_application):
    from tribunal.services.decisions import withdraw_application

    app = ready_application
    submit_application(app.owner, app.pk, "close-files", {"accepted": True, "name": "John Smith"})
    withdraw_application(app.owner, app.pk)
    login(client, app.owner)
    data = client.get(f"/api/applications/{app.pk}/files/").json()
    assert not data["can_upload"] and len(data["items"]) == 4
