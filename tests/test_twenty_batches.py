import json
from pathlib import Path
import pytest
from django.core.exceptions import PermissionDenied, ValidationError, ObjectDoesNotExist
from django.db import DatabaseError, transaction
from tribunal import models as m
from tribunal.services.identity import add_other_party, activate_pending_links, cancel_pending_link, link_party, set_account_status, enroll_council
from tribunal.services.historical import stage, publish
from tribunal.services.decisions import add_appeal_information, withdraw_application
from tribunal.services.applications import submit_application
from tribunal.services.reports import create_request, send_request, complete_request, create_recording, finalize_recording, cancel_request, review_transcript
from tribunal.services.request_contracts import request_version
from tribunal.services.media import correct_transcript, report_recordings
from tests.test_own_requests import filed, sent, login
from tests.test_closed_case_intake import closed_case, prepare
from tests.test_backend_followups import recorded

pytestmark = pytest.mark.django_db


@pytest.fixture
def pending_filing(closed_case, people):
    original, spouse, party = closed_case
    app = prepare(spouse, original.case, people)
    submit_application(spouse, app.pk, "twenty-pending", {"accepted": True, "name": "Jane Smith"})
    app.refresh_from_db()
    return app


def test_own_supplement_capability_version_http_and_exact_replay(client, pending_filing):
    app = pending_filing
    login(client, app.owner)
    detail = f"/api/applications/{app.pk}/"
    assert client.get(detail).json()["can_supplement"]
    url = f"/api/appeals/{app.pk}/additions/"
    payload = {"text": "New synthetic evidence", "expected_version": app.current_version, "idempotency_key": "supplement-one"}
    for bad in [{"idempotency_key": None}, {"expected_version": app.current_version+1}]:
        assert client.post(url, {**payload, **bad}, content_type="application/json").status_code == 422
    first = client.post(url, payload, content_type="application/json")
    assert first.status_code == 201
    assert client.post(url, payload, content_type="application/json").json() == first.json()
    assert client.post(url, {**payload, "text": "Different"}, content_type="application/json").status_code == 422
    assert m.AppealSupplement.objects.filter(application=app).count() == 1
    row = client.get(detail).json()["supplements"][0]
    assert row["id"] == first.json()["id"] and row["idempotency_key"] == "supplement-one"
    withdraw_application(app.owner, app.pk)
    assert not client.get(detail).json()["can_supplement"]
    assert client.post(url, payload, content_type="application/json").json() == first.json()


def test_supplement_evidence_rejects_wrong_scope_pending_and_old_version(pending_filing, people):
    app = pending_filing
    attachment = m.Attachment.objects.create(application=app, owner=app.owner, case=app.case, category="EXTRA")
    file = m.FileVersion.objects.create(attachment=attachment, number=1, object_key="twenty/evidence1", byte_count=5, sha256="a"*64)
    with pytest.raises(PermissionDenied):
        add_appeal_information(app.owner, app.pk, "Evidence", [str(file.pk)])
    m.FileTechnicalEvent.objects.create(file=file, task="scan", result="clean")
    assert add_appeal_information(app.owner, app.pk, "Evidence", [str(file.pk)]).manifest[0]["id"] == str(file.pk)
    newer = m.FileVersion.objects.create(attachment=attachment, number=2, object_key="twenty/evidence2", byte_count=5, sha256="b"*64)
    with pytest.raises(PermissionDenied):
        add_appeal_information(app.owner, app.pk, "Old original", [str(file.pk)])
    for value in ["bad", [str(file.pk), str(file.pk)]]:
        with pytest.raises(ValidationError):
            add_appeal_information(app.owner, app.pk, "Bad list", value)
    with pytest.raises(PermissionDenied):
        add_appeal_information(people["admin"], app.pk, "Not owner")


def test_capture_metadata_and_replay_are_retained(filed, people):
    row = sent(filed, people, "interview")
    report = complete_request(people["admin"], row.pk, {"text": "Synthetic"})
    attachment = m.Attachment.objects.create(case=filed.case, proceeding=filed.proceeding, category="REC", visibility="council")
    file = m.FileVersion.objects.create(attachment=attachment, number=1, object_key="twenty/capture", mime_type="video/webm", byte_count=5, sha256="a"*64)
    m.FileTechnicalEvent.objects.create(file=file, task="scan", result="clean")
    notice = {"acknowledged": True, "language": "en", "text": "Synthetic fixture notice"}
    recording = create_recording(people["admin"], file.pk, report_id=report.pk, notice_recorded=True, duration_ms=1234, recording_notice=notice)
    assert create_recording(people["admin"], file.pk, report_id=report.pk, notice_recorded=True, duration_ms=1234, recording_notice=notice).pk == recording.pk
    data = report_recordings(people["admin"], report.pk)["items"][0]
    assert data["duration_ms"] == 1234 and data["captured_by"] == str(people["admin"].pk) and data["recording_notice"] == notice
    for duration in [-1, "1234", True, 2**63]:
        with pytest.raises(ValidationError):
            create_recording(people["admin"], file.pk, report_id=report.pk, duration_ms=duration)
    with pytest.raises(ValidationError):
        create_recording(people["admin"], file.pk, report_id=report.pk, duration_ms=4321)
    with pytest.raises(DatabaseError), transaction.atomic():
        m.Recording.objects.filter(pk=recording.pk).update(duration_ms=4321)


def test_transcript_correction_replay_does_not_inherit_review(client, filed, people):
    recording, report = recorded(filed, people)
    run = finalize_recording(people["admin"], recording.pk)
    m.ProcessingRun.objects.filter(pk=run.pk).update(state="completed")
    original = m.TranscriptRevision.objects.create(recording=recording, run=run, number=1, language="en", text="Synthetic original")
    review_transcript(people["admin"], original.pk)
    login(client, people["admin"])
    url = f"/api/transcripts/{original.pk}/correct/"
    data = {"text": "Synthetic correction", "segments": [], "expected_version": 1}
    response = client.post(url, data, content_type="application/json")
    assert response.status_code == 201 and response.json()["version"] == 2 and not response.json()["reviewed"]
    assert client.post(url, data, content_type="application/json").json() == response.json()
    assert client.post(url, {**data, "text": "Changed stale write"}, content_type="application/json").status_code == 422
    assert m.TranscriptRevision.objects.get(pk=original.pk).text == "Synthetic original"
    login(client, people["member"])
    assert client.get(f"/api/transcripts/{response.json()['id']}/").status_code in {403,404}


def test_media_pagination_rejects_invalid_offsets(client, filed, people):
    recording, report = recorded(filed, people)
    login(client, people["admin"])
    url = f"/api/reports/{report.pk}/recordings/"
    for key in ["offset", "transcript_offset"]:
        assert client.get(url, {key: -1}).status_code == 422
    assert client.get(url, {"offset": 1}).json() == {"items": [], "next_offset": None}


@pytest.mark.parametrize("email,first,last", [("bad", "Jane", "Smith"), (None, "Jane", "Smith"), ("jane@example.test", "", "Smith"), ("jane@example.test", [], "Smith")])
def test_pending_link_input_rejects_invalid_fields(filed, people, email, first, last):
    with pytest.raises(ValidationError):
        add_other_party(people["admin"], filed.case_id, first, last, email)


def test_pending_duplicate_reuse_cancellation_and_no_late_activation(filed, people):
    pending = add_other_party(people["admin"], filed.case_id, "Jane", "Smith", " JANE@EXAMPLE.TEST ")
    assert add_other_party(people["secretary"], filed.case_id, "Jane", "Smith", "jane@example.test").pk == pending.pk
    with pytest.raises(ValidationError):
        add_other_party(people["admin"], filed.case_id, "Different", "Smith", "jane@example.test")
    cancel_pending_link(people["secretary"], pending.pk)
    assert cancel_pending_link(people["secretary"], pending.pk).state == "cancelled"
    account = m.Account.objects.create_user(email="jane@example.test", email_verified=True)
    assert activate_pending_links(account) == []
    assert not m.Party.objects.filter(case=filed.case, account=account).exists()


def test_pending_activation_requires_current_recorded_authority(filed, people):
    pending = add_other_party(people["secretary"], filed.case_id, "Jane", "Smith", "jane@example.test")
    m.Account.objects.filter(pk=people["secretary"].pk).update(is_active=False)
    account = m.Account.objects.create_user(email="jane@example.test", email_verified=True)
    assert activate_pending_links(account) == []
    pending.refresh_from_db()
    assert pending.state == "needs_review" and not pending.activated_party_id
    assert not m.Party.objects.filter(case=filed.case, account=account).exists()


def test_link_requires_applicant_and_rechecks_closed_case_state(filed, people):
    with pytest.raises(ValidationError):
        link_party(people["admin"], filed.case, people["member"])
    account = m.Account.objects.create_user(email="linked@example.test", email_verified=True)
    party = link_party(people["secretary"], filed.case, account)
    assert link_party(people["admin"], filed.case, account).pk == party.pk
    assert m.Party.objects.filter(case=filed.case, account=account).count() == 1


def test_private_historical_workspace_and_published_source_retention(people):
    record = stage(people["admin"], {"number": "PRIVATE-HISTORY", "status": "closed"})
    other = m.Account.objects.create_user(email="other-admin@example.test", role="admin", email_verified=True)
    with pytest.raises(ObjectDoesNotExist):
        publish(other, record.pk)
    case = publish(people["admin"], record.pk)
    assert publish(people["admin"], record.pk).pk == case.pk
    with pytest.raises(DatabaseError), transaction.atomic():
        m.HistoricalWorkspace.objects.filter(pk=record.pk).update(payload={"erased": True})


@pytest.mark.parametrize("extra", [{"number": 123}, {"parties": "bad"}, {"parties": [{"slot":"A"},{"slot":"A"}]},
    {"parties": [{"slot":"A", "name":[]}]}, {"status": []}])
def test_historical_invalid_payload_does_not_publish(people, extra):
    row = stage(people["admin"], {"number": "BAD-HISTORY", "status": "closed", **extra})
    with pytest.raises(ValidationError):
        publish(people["admin"], row.pk)
    assert not m.Case.objects.filter(number="BAD-HISTORY").exists()


def test_account_status_requires_boolean_and_retains_last_admin(people):
    with pytest.raises(ValidationError):
        set_account_status(people["admin"], people["member"].pk, "false")
    with pytest.raises(ValidationError):
        set_account_status(people["secretary"], people["admin"].pk, False)
    for email in [None, "not-an-email"]:
        with pytest.raises(ValidationError):
            enroll_council(people["admin"], email, "New", "Member")
    target = set_account_status(people["admin"], people["member"].pk, False)
    assert not target.is_active


def test_request_cancel_uses_bound_identity_and_revokes_external_capability(client, filed, people):
    row = create_request(people["admin"], filed.proceeding_id, filed.party_id, "external_priest", "Synthetic priest request", [])
    token = send_request(people["admin"], row.pk)
    row.refresh_from_db()
    with pytest.raises(ValidationError):
        cancel_request(people["admin"], row.pk, "stale")
    assert cancel_request(people["admin"], row.pk, request_version(row)).state == "cancelled"
    assert client.get(f"/external/reports/{row.pk}/", HTTP_AUTHORIZATION=f"Bearer {token}").status_code == 403
    assert cancel_request(people["admin"], row.pk, request_version(row)).state == "cancelled"
    with pytest.raises(ValidationError):
        send_request(people["admin"], row.pk)


def test_reconciliation_inventory_covers_every_approved_table_without_completion_claim():
    root = Path(__file__).resolve().parents[1]
    inventory = json.loads((root/"docs/implementation/schema-reconciliation.json").read_text())
    approved = json.loads((root/"docs/architecture/build-spec/schema.json").read_text())
    assert {x["approved_table"] for x in inventory["tables"]} == {x["name"] for x in approved["tables"]}
    assert inventory["candidate_mapped_count"]+inventory["unmapped_count"] == 151
    assert all(x["status"].endswith("requires_review") for x in inventory["tables"])


@pytest.mark.django_db(transaction=True)
def test_concurrent_party_link_reuses_one_party_and_claim(filed, people):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    from django.db import connection, connections
    from tribunal.services.common import lock_key
    if connection.vendor != "postgresql":
        pytest.skip("PostgreSQL canonical-person serialization")
    account = m.Account.objects.create_user(email="concurrent-link@example.test", email_verified=True)
    started = Event()
    def link():
        try:
            started.set()
            return link_party(people["admin"], filed.case, account).pk
        finally:
            connections.close_all()
    with ThreadPoolExecutor(max_workers=1) as pool:
        with transaction.atomic():
            lock_key(f"person:{account.person_id}")
            future = pool.submit(link)
            assert started.wait(timeout=5)
            first = link_party(people["admin"], filed.case, account)
        assert future.result(timeout=10) == first.pk
    assert m.Party.objects.filter(case=filed.case, account=account).count() == 1
    assert m.OpenCaseClaim.objects.get(person=account.person).case_id == filed.case_id


@pytest.mark.django_db(transaction=True)
def test_concurrent_supplement_retry_creates_one_record(pending_filing):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    from django.db import connection, connections
    if connection.vendor != "postgresql":
        pytest.skip("PostgreSQL supplement serialization")
    app = pending_filing
    started = Event()
    def supplement():
        try:
            started.set()
            return add_appeal_information(app.owner, app.pk, "Concurrent synthetic information", idempotency_key="concurrent-supplement").pk
        finally:
            connections.close_all()
    with ThreadPoolExecutor(max_workers=1) as pool:
        with transaction.atomic():
            m.Application.objects.select_for_update().get(pk=app.pk)
            future = pool.submit(supplement)
            assert started.wait(timeout=5)
            first = add_appeal_information(app.owner, app.pk, "Concurrent synthetic information", idempotency_key="concurrent-supplement")
        assert future.result(timeout=10) == first.pk
    assert m.AppealSupplement.objects.filter(application=app).count() == 1
