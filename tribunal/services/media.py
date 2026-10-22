"""Council original-media reads; generated content requires exact version review."""
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
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


def transcription_ready(revision):
    recording = revision.recording
    return bool(recording.finalized_at and revision.run.file_id == recording.file_id
        and revision.run.purpose == "transcription" and revision.run.state == "completed"
        and safe_file(recording.file))


def transcript_for(actor, revision_id):
    staff(actor)
    revision = m.TranscriptRevision.objects.select_related(
        "recording__report__request__case", "recording__file__attachment", "run").get(pk=revision_id)
    if (not transcription_ready(revision) or (not can_review(actor, revision.recording)
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


def report_recordings(actor, report_id):
    staff(actor)
    report = m.Report.objects.select_related("request__case").get(pk=report_id)
    if report.request.kind in {"medical", "psychological"}:
        raise PermissionDenied("Assessment recordings use their separate protected workflow.")
    items = []
    for recording in m.Recording.objects.filter(report=report).select_related(
            "file__attachment", "report__request__case", "report__request__proceeding").order_by("created_at", "id"):
        run = m.ProcessingRun.objects.filter(file=recording.file, purpose="transcription").order_by("-attempt").first()
        valid_file = safe_file(recording.file)
        writable = can_review(actor, recording)
        open_source = bool(report.request.case.status == "open" and report.request.proceeding.status == "open")
        transcripts = []
        if valid_file:
            for revision in m.TranscriptRevision.objects.filter(recording=recording).select_related("run").order_by("language", "kind", "number"):
                reviewed = m.TranscriptReview.objects.filter(revision=revision).exists()
                if not transcription_ready(revision) or not (writable or reviewed):
                    continue
                transcripts.append({"id": str(revision.pk), "kind": revision.kind,
                    "language": revision.language, "version": revision.number, "reviewed": reviewed,
                    "actor": str(revision.actor_id) if revision.actor_id else None,
                    "timestamp": revision.created_at.isoformat()})
        items.append({"id": str(recording.pk), "file_id": str(recording.file_id),
            "mime_type": recording.file.mime_type, "byte_count": recording.file.byte_count,
            "duration_ms": None, "captured_by": None,
            "notice_recorded": recording.notice_recorded, "created_at": recording.created_at.isoformat(),
            "finalized_at": recording.finalized_at.isoformat() if recording.finalized_at else None,
            "download_url": f"/api/files/{recording.file_id}/" if valid_file else None,
            "processing": ({"run_id": str(run.pk), "state": "succeeded" if run.state == "completed" else run.state,
                "attempt": run.attempt, "engine": run.engine, "updated_at": None,
                "safe_error": "Processing failed; the original is retained." if run.state == "failed" else "",
                "can_retry": bool(valid_file and writable and open_source and run.state == "failed")}
                if run else None), "transcripts": transcripts,
            "can_finalize": bool(valid_file and writable and open_source and recording.notice_recorded and not recording.finalized_at)})
    return {"items": items}


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
