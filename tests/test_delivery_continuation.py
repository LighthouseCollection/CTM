import hashlib
import io
import zipfile
from datetime import datetime
from unittest.mock import Mock, patch
import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import override_settings
from django.utils import timezone
from tribunal import models as m
from tribunal.tasks import claim_delivery, dispatch_outbox
from tribunal.services.communications import send_message, acknowledge_message
from tribunal.services.common import notify_manager
from tribunal.services.retention import process_drafts
from tribunal.services.applications import allocate_case_number
from tribunal.services.documents import extract_local
from tribunal.services.files import private_path, write_private_original
from tribunal.services.search import search, index_text
from tests.test_own_requests import filed, login

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize("content,recipients", [(None, []), ([], []), ("Text", "bad"), ("Text", []), ("Text", [1,2,3])])
def test_message_input_is_typed(filed, people, content, recipients):
    with pytest.raises(ValidationError):
        send_message(people["admin"], filed.case_id, content, recipients)


def test_message_replay_and_private_first_read_receipts(client, filed, people):
    spouse = m.Account.objects.create_user(email="message-spouse@example.test", email_verified=True)
    party = m.Party.objects.create(case=filed.case, account=spouse, person=spouse.person, slot="B")
    args = (people["admin"], filed.case_id, "Synthetic private update", [str(filed.party_id), str(party.pk)])
    message = send_message(*args, idempotency_key="one-message")
    assert send_message(*args, idempotency_key="one-message").pk == message.pk
    assert m.Message.objects.filter(case=filed.case).count() == 1
    with pytest.raises(ValidationError):
        send_message(people["admin"], filed.case_id, "Changed", args[3], idempotency_key="one-message")
    login(client, filed.owner)
    listing = f"/api/cases/{filed.case_id}/messages/"
    first = client.get(listing).json()["items"][0]
    assert first["receipts"] == [{"party_id": str(filed.party_id), "read_at": None}]
    read = f"/api/messages/{message.pk}/read/"
    receipt = client.post(read, {}, content_type="application/json").json()
    assert client.post(read, {}, content_type="application/json").json() == receipt
    assert m.MessageRecipient.objects.get(message=message, party=party).read_at is None
    assert client.get(listing, {"offset": 1}).json() == {"items": [], "next_offset": None}
    assert client.get(listing, {"offset": -1}).status_code == 422
    login(client, people["member"])
    assert client.post(read, {}, content_type="application/json").status_code == 403


def test_applicant_cannot_fabricate_other_delivery_channel(filed):
    for channel in ["email", "call"]:
        with pytest.raises(PermissionDenied):
            send_message(filed.owner, filed.case_id, "Own text", [str(filed.party_id)], channel=channel)


@override_settings(EMAIL_HOST="synthetic-configured-host")
def test_message_dispatch_rechecks_recipient_account(filed, people, mailoutbox):
    message = send_message(people["admin"], filed.case_id, "Synthetic notice", [str(filed.party_id)])
    # Existing intake jobs are outside this test's delivery scope.
    m.Outbox.objects.exclude(kind="message").update(due_at=timezone.now()+timezone.timedelta(days=1))
    m.Account.objects.filter(pk=filed.owner_id).update(is_active=False)
    assert dispatch_outbox() == 0 and not mailoutbox
    job = m.Outbox.objects.get(payload__message=str(message.pk))
    assert job.discarded_at and job.delivered_at is None


@override_settings(EMAIL_HOST="synthetic-configured-host")
def test_applicant_message_routes_to_current_manager(filed, people, mailoutbox):
    filed.case.assigned_member = people["member"]
    filed.case.save(update_fields=["assigned_member"])
    send_message(filed.owner, filed.case_id, "Private question", [str(filed.party_id)])
    m.Outbox.objects.exclude(kind="applicant_message").update(due_at=timezone.now()+timezone.timedelta(days=1))
    m.Case.objects.filter(pk=filed.case_id).update(assigned_member=people["president"])
    assert dispatch_outbox() == 1
    assert mailoutbox[0].to == [people["president"].email]


@override_settings(EMAIL_HOST="synthetic-configured-host")
def test_obsolete_draft_warning_is_discarded_after_edit(unpaid_application, mailoutbox):
    app = unpaid_application
    m.Application.objects.filter(pk=app.pk).update(last_activity=timezone.now()-timezone.timedelta(days=174))
    assert process_drafts()["warned"] == 1
    m.Application.objects.filter(pk=app.pk).update(last_activity=timezone.now())
    assert dispatch_outbox() == 0 and not mailoutbox
    job = m.Outbox.objects.get(kind="draft_expiring")
    assert job.discarded_at and not job.delivered_at


def test_outbox_lease_fences_stale_worker_success(people):
    job = m.Outbox.objects.create(key="fenced-worker", kind="synthetic", recipient=people["member"])
    replacement = []
    def reassign(events):
        m.Outbox.objects.filter(pk=job.pk).update(lease_until=timezone.now()-timezone.timedelta(seconds=1))
        replacement.extend(claim_delivery(job.pk))
    with patch("tribunal.tasks.deliver", side_effect=reassign):
        assert dispatch_outbox() == 0
    job.refresh_from_db()
    assert replacement and job.lease_token == replacement[0].lease_token and not job.delivered_at


def test_outbox_limits_and_exponential_failure_backoff(people):
    for limit in [0, -1, 501, True, "50"]:
        with pytest.raises(ValueError):
            dispatch_outbox(limit)
    job = m.Outbox.objects.create(key="backoff", kind="synthetic", recipient=people["member"])
    with override_settings(EMAIL_HOST=""):
        before = timezone.now()
        assert dispatch_outbox() == 0
        job.refresh_from_db()
        assert job.attempts == 1 and job.due_at >= before+timezone.timedelta(minutes=2)
        m.Outbox.objects.filter(pk=job.pk).update(due_at=timezone.now())
        before = timezone.now()
        dispatch_outbox()
        job.refresh_from_db()
        assert job.attempts == 2 and job.due_at >= before+timezone.timedelta(minutes=4)
        assert not job.lease_token and not job.delivered_at


def test_invalid_manager_does_not_receive_private_portal_notification(filed, people):
    filed.case.assigned_member = filed.owner
    filed.case.save(update_fields=["assigned_member"])
    notify_manager(filed.case, "applicant_message", filed)
    assert not m.Notification.objects.filter(recipient=filed.owner, kind="applicant_message").exists()
    assert m.Notification.objects.filter(kind="manager_authority_review", recipient=people["admin"]).exists()


@pytest.mark.parametrize("value", [datetime(2026,1,1), "now", 0])
def test_number_allocator_rejects_naive_or_non_timestamp(value):
    with pytest.raises(ValidationError):
        allocate_case_number(value)


@pytest.mark.parametrize("data", [None, [], {}, {"hits": None}, {"hits": "bad"}, {"hits": [{}]*101}])
def test_malformed_search_candidate_response_fails_closed(people, monkeypatch, data):
    monkeypatch.setenv("MEILI_URL", "https://synthetic-search.test")
    monkeypatch.setenv("MEILI_MASTER_KEY", "synthetic-unused-key")
    response = Mock()
    response.json.return_value = data
    with patch("tribunal.services.search.requests.post", return_value=response), pytest.raises(ValidationError):
        search(people["member"], "synthetic")


def test_malformed_hit_ids_are_ignored_and_unsafe_text_not_indexed(filed, people, monkeypatch):
    monkeypatch.setenv("MEILI_URL", "https://synthetic-search.test")
    monkeypatch.setenv("MEILI_MASTER_KEY", "synthetic-unused-key")
    source = filed.attachments.get(category="MC").versions.first()
    response = Mock()
    response.json.return_value = {"hits": [None, [], {}, {"file_id":"bad"}, {"file_id":str(source.pk)}]}
    with patch("tribunal.services.search.requests.post", return_value=response):
        assert search(people["member"], "synthetic")["returned_count"] == 1
    text = m.DocumentText.objects.create(file=source, engine="synthetic", text="Synthetic document")
    m.FileTechnicalEvent.objects.create(file=source, task="scan", result="pending")
    with patch("tribunal.services.search.requests.post") as provider:
        assert index_text(text) is None
        provider.assert_not_called()


def docx_file(app, settings, tmp_path, xml):
    settings.MEDIA_ROOT = tmp_path
    stream = io.BytesIO()
    with zipfile.ZipFile(stream,"w") as archive:
        archive.writestr("word/document.xml", xml)
    data = stream.getvalue()
    attachment = m.Attachment.objects.create(application=app, owner=app.owner, category="EXTRA")
    file = m.FileVersion.objects.create(attachment=attachment, number=1, object_key=f"docx/{attachment.pk}.docx",
        mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        byte_count=len(data), sha256=hashlib.sha256(data).hexdigest())
    m.FileTechnicalEvent.objects.create(file=file, task="scan", result="clean")
    write_private_original(private_path(file.object_key), data)
    return file


def test_local_extraction_integrity_and_idempotent_derivative(unpaid_application, settings, tmp_path):
    source = docx_file(unpaid_application, settings, tmp_path, '<w:document xmlns:w="synthetic"><w:t>Synthetic text</w:t></w:document>')
    first = extract_local(source.pk)
    assert first.text == "Synthetic text" and extract_local(source.pk).pk == first.pk
    private_path(source.object_key).write_bytes(b"tampered")
    with pytest.raises(ValidationError):
        extract_local(source.pk)
    assert m.DocumentText.objects.filter(file=source).count() == 1


@pytest.mark.parametrize("encoding", ["utf-8", "utf-16"])
def test_docx_entity_declarations_are_not_processed(unpaid_application, settings, tmp_path, encoding):
    source = docx_file(unpaid_application, settings, tmp_path, '<!DOCTYPE doc [<!ENTITY secret "not processed">]><doc>&secret;</doc>'.encode(encoding))
    with pytest.raises(ValidationError):
        extract_local(source.pk)
    assert not m.DocumentText.objects.filter(file=source).exists()


def test_edit_after_digest_claim_defers_without_counting_provider_failure(people):
    from tribunal.tasks import deliver as actual_delivery
    case = m.Case.objects.create(number="DIGEST-QUIET", assigned_member=people["member"])
    job = m.Outbox.objects.create(key="old-digest", kind="answer_changed", case=case, recipient=people["member"])
    deadline = timezone.now()+timezone.timedelta(minutes=10)
    def editing(events):
        m.Outbox.objects.create(key="new-digest", kind="file_uploaded", case=case, recipient=people["member"], due_at=deadline)
        actual_delivery(events)
    with patch("tribunal.tasks.deliver", side_effect=editing):
        assert dispatch_outbox() == 0
    job.refresh_from_db()
    assert job.due_at == deadline and job.attempts == 0 and not job.delivered_at and not job.lease_token


def test_number_capacity_retains_counter_and_rejects_reset():
    from django.db import connection, transaction, DatabaseError
    if connection.vendor != "postgresql":
        pytest.skip("PostgreSQL monotonic counter")
    target = timezone.now().astimezone(__import__("zoneinfo").ZoneInfo("America/Los_Angeles")).date()
    m.CaseNumberCounter.objects.create(date=target, last_value=99)
    with pytest.raises(ValidationError):
        allocate_case_number()
    assert m.CaseNumberCounter.objects.get(date=target).last_value == 99
    with pytest.raises(DatabaseError), transaction.atomic():
        m.CaseNumberCounter.objects.filter(date=target).update(last_value=0)


def test_byte_route_does_not_expose_corrupt_length(client, unpaid_application, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    source = unpaid_application.attachments.get(category="MC").versions.first()
    write_private_original(private_path(source.object_key), b"unexpected bytes")
    login(client, unpaid_application.owner)
    for method in [client.get, client.head]:
        response = method(f"/api/files/{source.pk}/", HTTP_RANGE="bytes=0-3")
        assert response.status_code == 503 and "Content-Range" not in response


@pytest.mark.django_db(transaction=True)
def test_concurrent_message_send_reuses_one_message_and_notification(filed, people):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    from django.db import connection, connections, transaction
    from tribunal.services.common import lock_key
    if connection.vendor != "postgresql":
        pytest.skip("PostgreSQL message replay serialization")
    started = Event()
    key = "concurrent-message"
    def send():
        try:
            started.set()
            return send_message(people["admin"], filed.case_id, "Synthetic message", [str(filed.party_id)], idempotency_key=key).pk
        finally:
            connections.close_all()
    with ThreadPoolExecutor(max_workers=1) as pool:
        with transaction.atomic():
            lock_key(f"message:{filed.case_id}:{people['admin'].pk}:{key}")
            future = pool.submit(send)
            assert started.wait(timeout=5)
            first = send_message(people["admin"], filed.case_id, "Synthetic message", [str(filed.party_id)], idempotency_key=key)
        assert future.result(timeout=10) == first.pk
    assert m.Message.objects.filter(case=filed.case).count() == 1
    assert m.Outbox.objects.filter(kind="message", payload__message=str(first.pk)).count() == 1
