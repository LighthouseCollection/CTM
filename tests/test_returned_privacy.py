"""F08 / AS-F08: returned corrections stay private through API and byte delivery."""
from unittest.mock import patch, Mock
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from tribunal import models as m
from tribunal.services.applications import submit_application, review_application, save_answers
from tribunal.services.files import upload, private_path, write_private_original
from tribunal.services.search import search, index_text

pytestmark = pytest.mark.django_db


def correction(app, people):
    formal = submit_application(app.owner, app.pk, "f08-first", {"accepted": True, "name": "John Smith"})
    app.refresh_from_db()
    review_application(people["admin"], app.pk, "reject", "Correct the filing.")
    app.refresh_from_db()
    app.case.assigned_member = people["member"]
    app.case.save(update_fields=["assigned_member"])
    answers = dict(formal.revision.answers, statement="PRIVATE CORRECTION")
    draft = save_answers(app.owner, app.pk, answers, app.current_version)
    attachment = app.attachments.get(category="MC")
    previous = attachment.versions.first()
    replacement = upload(app.owner, SimpleUploadedFile("replacement.pdf", b"%PDF-private"),
                         "MC", app_id=app.pk, attachment_id=attachment.pk)
    app.refresh_from_db()
    return app, formal, draft, previous, replacement


def login(client, actor):
    client.force_login(actor, backend="allauth.account.auth_backends.AuthenticationBackend")


def test_returned_http_snapshot_and_bytes(client, ready_application, people, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    settings.CTM_SCAN_REQUIRED = False
    app, formal, draft, old, new = correction(ready_application, people)
    write_private_original(private_path(old.object_key), b"%PDF-original")
    write_private_original(private_path(new.object_key), b"%PDF-private")
    login(client, app.owner)
    assert client.get(f"/api/applications/{app.pk}/").json()["answers"] == draft.answers
    assert client.get(f"/api/files/{new.pk}/").status_code == 200
    for role in ["member", "secretary", "admin"]:
        login(client, people[role])
        data = client.get(f"/api/applications/{app.pk}/").json()
        assert data["answers"] == formal.revision.answers
        assert data["version"] == formal.revision.number
        history = client.get(f"/api/applications/{app.pk}/history/").json()["items"]
        assert [row["id"] for row in history] == [str(formal.revision_id)]
        for suffix in ["", "?history=1"]:
            listing = client.get(f"/api/cases/{app.case_id}/files/{suffix}").json()["items"]
            ids = {row["id"] for row in listing}
            assert str(old.pk) in ids and str(new.pk) not in ids
        for method, suffix, headers in [("get", "", {}), ("head", "", {}),
                                        ("get", "", {"HTTP_RANGE": "bytes=0-3"}),
                                        ("get", "?view=1", {})]:
            response = getattr(client, method)(f"/api/files/{new.pk}/{suffix}", **headers)
            assert response.status_code in {403, 404}
        assert client.get(f"/api/files/{old.pk}/").status_code == 200
        audit = client.get(f"/api/cases/{app.case_id}/audit/").json()["items"]
        assert not {str(draft.pk), str(new.pk)} & {row["source_id"] for row in audit}
    assert not m.Notification.objects.filter(kind__in=["answer_changed", "file_uploaded"]).exists()
    assert not m.Outbox.objects.filter(kind__in=["answer_changed", "file_uploaded"]).exists()
    second = submit_application(app.owner, app.pk, "f08-second", expected_version=app.current_version)
    assert second.attestation == {"original_submission": str(formal.pk)}
    login(client, people["member"])
    assert client.get(f"/api/applications/{app.pk}/").json()["answers"] == draft.answers
    assert client.get(f"/api/files/{new.pk}/").status_code == 200
    assert app.submissions.count() == 2


def test_returned_search_reauthorizes_cached_hits(ready_application, people, settings, monkeypatch):
    settings.CTM_SCAN_REQUIRED = False
    app, formal, draft, old, new = correction(ready_application, people)
    derivative = m.DocumentText.objects.create(file=new, text="PRIVATE CORRECTION", language="en")
    monkeypatch.setenv("MEILI_URL", "https://search.example.test")
    monkeypatch.setenv("MEILI_MASTER_KEY", "synthetic-test")
    response = Mock()
    response.json.return_value = {"hits": [{"file_id": str(new.pk)}, {"file_id": str(old.pk)}]}
    with patch("tribunal.services.search.requests.post", return_value=response) as post:
        assert index_text(derivative) is None
        post.assert_not_called()
        result = search(people["member"], "correction")
    assert [row["file_id"] for row in result["items"]] == [str(old.pk)]
    assert result["returned_count"] == 1


def test_unsubmitted_intermediate_corrections_remain_private_after_resubmit(client, ready_application, people, settings):
    settings.CTM_SCAN_REQUIRED = False
    app, formal, draft, old, new = correction(ready_application, people)
    final = save_answers(app.owner, app.pk, dict(draft.answers, statement="FORMAL CORRECTION"), app.current_version)
    last = upload(app.owner, SimpleUploadedFile("final.pdf", b"%PDF-final"), "MC",
                  app_id=app.pk, attachment_id=old.attachment_id)
    app.refresh_from_db()
    submit_application(app.owner, app.pk, "f08-final", expected_version=app.current_version)
    login(client, people["member"])
    history = client.get(f"/api/applications/{app.pk}/history/").json()["items"]
    assert {row["id"] for row in history} == {str(formal.revision_id), str(final.pk)}
    assert client.get(f"/api/files/{new.pk}/").status_code in {403, 404}
    listing = client.get(f"/api/cases/{app.case_id}/files/?history=1").json()["items"]
    ids = {row["id"] for row in listing}
    assert str(new.pk) not in ids and {str(old.pk), str(last.pk)} <= ids
    review_application(people["admin"], app.pk, "reject", "Second return")
    detail = client.get(f"/api/applications/{app.pk}/").json()
    assert detail["answers"] == final.answers
    assert detail["version"] == final.number


def test_old_pending_alerts_are_hidden_and_discarded(client, ready_application, people, settings):
    from tribunal.services.common import notify_manager
    from tribunal.tasks import dispatch_outbox
    from django.utils import timezone
    settings.CTM_SCAN_REQUIRED = False
    app, formal, draft, old, new = correction(ready_application, people)
    # Represent pre-fix jobs retained in the database, without sending any email.
    notify_manager(app.case, "answer_changed", draft)
    notify_manager(app.case, "file_uploaded", new)
    m.Outbox.objects.exclude(kind__in=["answer_changed", "file_uploaded"]).update(
        due_at=timezone.now() + timezone.timedelta(days=1))
    login(client, people["member"])
    inbox = client.get("/api/notifications/").json()
    assert inbox["items"] == [] and inbox["unread_count"] == 0
    with patch("tribunal.tasks.EmailMessage.send") as send:
        assert dispatch_outbox() == 0
        send.assert_not_called()
    jobs = m.Outbox.objects.filter(kind__in=["answer_changed", "file_uploaded"])
    assert jobs.count() == 2
    assert not jobs.filter(discarded_at__isnull=True).exists()
    assert not jobs.filter(delivered_at__isnull=False).exists()
