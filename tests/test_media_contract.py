import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from tribunal import models as m
from tribunal.services.media import retry_processing, transcript_for
from tribunal.services.reports import finalize_recording, review_transcript
from tests.test_own_requests import filed, login
from tests.test_backend_followups import recorded

pytestmark = pytest.mark.django_db


def output(recording, actor, *, number=1):
    run = finalize_recording(actor, recording.pk)
    m.ProcessingRun.objects.filter(pk=run.pk).update(state="completed", engine="synthetic-fixture")
    return m.TranscriptRevision.objects.create(recording=recording, run=run, number=number,
        language="en", text="Synthetic generated text", segments=[{"speaker": "A", "text": "Synthetic"}])


def test_recording_list_and_exact_transcript_review_gate(client, filed, people):
    recording, report = recorded(filed, people)
    revision = output(recording, people["admin"])
    listing = f"/api/reports/{report.pk}/recordings/"
    detail = f"/api/transcripts/{revision.pk}/"
    login(client, people["member"])
    row = client.get(listing).json()["items"][0]
    assert row["captured_by"] is None and row["duration_ms"] is None
    assert row["processing"]["state"] == "succeeded" and row["transcripts"] == []
    assert not row["can_finalize"]
    assert client.get(detail).status_code == 403
    assert client.post(detail+"review/", {}, content_type="application/json").status_code == 403
    login(client, people["admin"])
    response = client.get(detail)
    assert response["Cache-Control"] == "private, no-store"
    assert response.json()["text"] == revision.text and response.json()["segments"] == revision.segments
    assert client.post(detail+"review/", {}, content_type="application/json").status_code == 201
    assert client.post(detail+"review/", {}, content_type="application/json").status_code == 201
    assert m.TranscriptReview.objects.filter(revision=revision).count() == 1
    login(client, people["member"])
    assert client.get(detail).status_code == 200
    assert client.get(listing).json()["items"][0]["transcripts"][0]["reviewed"] is True
    login(client, filed.owner)
    assert client.get(listing).status_code == 403 and client.get(detail).status_code == 403


def test_new_version_needs_new_review_and_unsafe_original_hides_text(client, filed, people):
    recording, report = recorded(filed, people)
    revision = output(recording, people["admin"])
    review_transcript(people["admin"], revision.pk)
    newer = m.TranscriptRevision.objects.create(recording=recording, run=revision.run, number=2, language="en", text="Synthetic correction")
    with pytest.raises(ValidationError):
        review_transcript(people["admin"], revision.pk)
    login(client, people["member"])
    assert client.get(f"/api/transcripts/{revision.pk}/").status_code == 200
    assert client.get(f"/api/transcripts/{newer.pk}/").status_code == 403
    m.FileTechnicalEvent.objects.create(file=recording.file, task="scan", result="pending")
    login(client, people["admin"])
    assert client.get(f"/api/transcripts/{revision.pk}/").status_code == 403
    row = client.get(f"/api/reports/{report.pk}/recordings/").json()["items"][0]
    assert row["download_url"] is None and row["transcripts"] == []


def test_retry_creates_one_new_attempt_keeps_output_and_hides_raw_error(client, filed, people):
    recording, report = recorded(filed, people)
    run = finalize_recording(people["admin"], recording.pk)
    revision = m.TranscriptRevision.objects.create(recording=recording, run=run, number=1, language="en", text="Synthetic retained failed output")
    m.ProcessingRun.objects.filter(pk=run.pk).update(state="failed", error="sensitive provider diagnostic")
    login(client, people["admin"])
    row = client.get(f"/api/reports/{report.pk}/recordings/").json()["items"][0]
    assert row["processing"]["can_retry"]
    assert "sensitive" not in row["processing"]["safe_error"]
    url = f"/api/processing/{run.pk}/retry/"
    first = client.post(url, {}, content_type="application/json")
    assert first.status_code == 201 and first.json()["attempt"] == 2
    assert client.post(url, {}, content_type="application/json").json() == first.json()
    assert m.ProcessingRun.objects.filter(file=recording.file).count() == 2
    assert m.TranscriptRevision.objects.get(pk=revision.pk).text == revision.text
    assert m.Outbox.objects.filter(key=f"transcribe:{first.json()['id']}").count() == 1
    assert finalize_recording(people["admin"], recording.pk).pk == run.pk
    login(client, people["member"])
    assert client.post(url, {}, content_type="application/json").status_code == 403


def test_retry_rejects_active_attempt_and_wrong_case_output(filed, people):
    from django.db import DatabaseError, transaction
    recording, report = recorded(filed, people)
    run = finalize_recording(people["admin"], recording.pk)
    with pytest.raises(ValidationError):
        retry_processing(people["admin"], run.pk)
    other, other_report = recorded(filed, people)
    with pytest.raises(DatabaseError), transaction.atomic():
        m.TranscriptRevision.objects.create(recording=other, run=run, number=1, language="en", text="Wrong recording")


@pytest.mark.django_db(transaction=True)
def test_concurrent_retry_returns_one_new_attempt(filed, people):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    from django.db import connection, connections, transaction
    if connection.vendor != "postgresql":
        pytest.skip("PostgreSQL recording serialization")
    recording, report = recorded(filed, people)
    run = finalize_recording(people["admin"], recording.pk)
    m.ProcessingRun.objects.filter(pk=run.pk).update(state="failed")
    started = Event()

    def retry():
        try:
            started.set()
            return retry_processing(people["admin"], run.pk).pk
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=1) as pool:
        with transaction.atomic():
            m.Recording.objects.select_for_update().get(pk=recording.pk)
            future = pool.submit(retry)
            assert started.wait(timeout=5)
            first = retry_processing(people["admin"], run.pk)
        assert future.result(timeout=10) == first.pk
    assert m.ProcessingRun.objects.filter(file=recording.file).count() == 2
    assert m.Outbox.objects.filter(key=f"transcribe:{first.pk}").count() == 1
