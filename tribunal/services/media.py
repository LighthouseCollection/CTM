"""Council original-media reads; generated content requires exact version review."""
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db import connection
from tribunal.db.context import database_actor
import json
from tribunal import models as m
from tribunal.policy import staff, writer, administrator, open_proceeding
from .applications import safe_file
from .common import audit


def recording_reviewer(actor, recording):
    staff(actor)
    if recording.report_id:
        if recording.report.request.kind in {"medical", "psychological"}:
            raise PermissionDenied("Assessment processing is separate.")
        writer(actor, recording.report.request.case)
    else:
        administrator(actor)


def can_review(actor, recording):
    try:
        recording_reviewer(actor, recording)
        return True
    except PermissionDenied:
        return False


def transcription_ready(revision, actor=None):
    if connection.vendor == "postgresql" and actor is not None:
        with database_actor(actor), connection.cursor() as cursor:
            cursor.execute("SELECT public.ctm_media_readable('transcriptrevision',jsonb_build_object('id',%s::text))", [str(revision.pk)])
            return cursor.fetchone()[0]
    recording = revision.recording
    return bool(recording.finalized_at and revision.run.file_id == recording.file_id
        and revision.run.purpose == "transcription" and revision.run.state == "completed"
        and safe_file(recording.file))


def transcript_for(actor, revision_id):
    staff(actor)
    revision = m.TranscriptRevision.objects.select_related(
        "recording__report__request__case", "recording__file__attachment").get(pk=revision_id)
    if (not transcription_ready(revision, actor) or (not can_review(actor, revision.recording)
            and not m.TranscriptReview.objects.filter(revision=revision).exists())):
        raise PermissionDenied("This exact transcript version is not released for council reading.")
    return revision


def transcript_data(actor, revision):
    reviewed = m.TranscriptReview.objects.filter(revision=revision).exists()
    latest = not m.TranscriptRevision.objects.filter(recording=revision.recording,
        language=revision.language, kind=revision.kind, number__gt=revision.number).exists()
    return {"id": str(revision.pk), "recording_id": str(revision.recording_id),
        "run_id": str(revision.run_id), "kind": revision.kind, "language": revision.language,
        "version": revision.number, "text": revision.text, "segments": revision.segments,
        "reviewed": reviewed, "can_review": bool(latest and can_review(actor, revision.recording)),
        "timestamp": revision.created_at.isoformat()}


def processing_summary(actor, recording):
    if connection.vendor == "postgresql":
        with database_actor(actor), connection.cursor() as cursor:
            cursor.execute("SELECT public.ctm_media_status(%s)", [str(recording.file_id)])
            value = cursor.fetchone()[0]
        return json.loads(value) if isinstance(value, str) else value
    run = m.ProcessingRun.objects.filter(file=recording.file, purpose="transcription").order_by("-attempt").first()
    return ({"run_id": str(run.pk), "state": "succeeded" if run.state == "completed" else run.state,
        "attempt": run.attempt, "engine": run.engine, "updated_at": None,
        "safe_error": "Processing failed; the original is retained." if run.state == "failed" else ""} if run else None)


def report_recordings(actor, report_id, *, offset=0, transcript_offset=0):
    staff(actor)
    if type(offset) is not int or not 0 <= offset <= 2**63-52:
        raise ValidationError("Recording offset is outside the supported range.")
    if type(transcript_offset) is not int or not 0 <= transcript_offset <= 2**63-102:
        raise ValidationError("Transcript offset is outside the supported range.")
    report = m.Report.objects.select_related("request__case").get(pk=report_id)
    if report.request.kind in {"medical", "psychological"}:
        raise PermissionDenied("Assessment recordings use their separate protected workflow.")
    items = []
    rows = list(m.Recording.objects.filter(report=report).select_related(
            "file__attachment", "report__request__case", "report__request__proceeding").order_by("created_at", "id")[offset:offset+51])
    for recording in rows[:50]:
        processing = processing_summary(actor, recording)
        valid_file = safe_file(recording.file)
        writable = can_review(actor, recording)
        open_source = bool(report.request.case.status == "open" and report.request.proceeding.status == "open")
        transcripts = []
        transcript_rows = []
        if valid_file:
            transcript_rows = list(m.TranscriptRevision.objects.filter(recording=recording).order_by("language", "kind", "number")[transcript_offset:transcript_offset+101])
            for revision in transcript_rows[:100]:
                reviewed = m.TranscriptReview.objects.filter(revision=revision).exists()
                if not transcription_ready(revision, actor) or not (writable or reviewed):
                    continue
                transcripts.append({"id": str(revision.pk), "kind": revision.kind,
                    "language": revision.language, "version": revision.number, "reviewed": reviewed,
                    "actor": str(revision.actor_id) if revision.actor_id else None,
                    "timestamp": revision.created_at.isoformat()})
        if processing:
            processing["can_retry"] = bool(valid_file and writable and open_source and processing["state"] == "failed")
        items.append({"id": str(recording.pk), "file_id": str(recording.file_id),
            "mime_type": recording.file.mime_type, "byte_count": recording.file.byte_count,
            "duration_ms": recording.duration_ms, "captured_by": str(recording.captured_by_id) if recording.captured_by_id else None,
            "recording_notice": recording.recording_notice,
            "notice_recorded": recording.notice_recorded, "created_at": recording.created_at.isoformat(),
            "finalized_at": recording.finalized_at.isoformat() if recording.finalized_at else None,
            "download_url": f"/api/files/{recording.file_id}/" if valid_file else None,
            "processing": processing, "transcripts": transcripts,
            "transcripts_next_offset": transcript_offset+100 if len(transcript_rows)>100 else None,
            "can_finalize": bool(valid_file and writable and open_source and recording.notice_recorded and not recording.finalized_at)})
    return {"items": items, "next_offset": offset+50 if len(rows)>50 else None}


@transaction.atomic
def correct_transcript(actor, revision_id, text, segments, expected_version):
    revision = transcript_for(actor, revision_id)
    recording = m.Recording.objects.select_for_update(of=("self",)).select_related(
        "report__request__proceeding__case", "file__attachment").get(pk=revision.recording_id)
    recording_reviewer(actor, recording)
    if recording.report_id:
        open_proceeding(recording.report.request.proceeding)
    elif recording.file.attachment.case.status != "open":
        raise ValidationError("Historical transcript corrections require a separate reviewed workflow.")
    import json
    if (type(expected_version) is not int or expected_version < 1 or not isinstance(text, str)
            or not text.strip() or len(text)>5000000 or not isinstance(segments, list)
            or len(json.dumps(segments))>5000000):
        raise ValidationError("A bound version, nonempty text and bounded segment list are required.")
    latest = m.TranscriptRevision.objects.filter(recording=recording, language=revision.language,
        kind=revision.kind).order_by("-number").first()
    if latest.number != expected_version:
        if (latest.number == expected_version+1 and latest.actor_id == actor.pk
                and latest.text == text and latest.segments == segments):
            return latest
        raise ValidationError("A newer transcript version was saved. Reload before correcting.")
    row = m.TranscriptRevision.objects.create(recording=recording, run=revision.run,
        number=latest.number+1, language=revision.language, kind=revision.kind, text=text, segments=segments, actor=actor)
    audit(actor, "transcript_corrected", row, recording.file.attachment.case)
    return row


@transaction.atomic
def retry_processing(actor, run_id):
    staff(actor)
    source = m.ProcessingRun.objects.get(pk=run_id, purpose="transcription")
    recording = m.Recording.objects.select_for_update(of=("self",)).select_related(
        "report__request__case", "report__request__proceeding", "file__attachment").get(file=source.file)
    recording_reviewer(actor, recording)
    if recording.report_id:
        open_proceeding(recording.report.request.proceeding)
    elif recording.file.attachment.case.status != "open":
        raise ValidationError("Closed-case processing cannot be restarted.")
    if not recording.finalized_at or not safe_file(recording.file):
        raise ValidationError("Safe finalized original required.")
    if source.state != "failed":
        raise ValidationError("Only a failed processing attempt can be retried.")
    latest = m.ProcessingRun.objects.filter(file=source.file, purpose=source.purpose).order_by("-attempt").first()
    if latest.attempt > source.attempt:
        return m.ProcessingRun.objects.get(file=source.file, purpose=source.purpose, attempt=source.attempt+1)
    run = m.ProcessingRun.objects.create(file=source.file, purpose=source.purpose, attempt=source.attempt+1)
    m.Outbox.objects.create(key=f"transcribe:{run.pk}", kind="transcribe", case=recording.file.attachment.case,
        payload={"run": str(run.pk)})
    audit(actor, "transcription_retried", run, recording.file.attachment.case)
    return run
