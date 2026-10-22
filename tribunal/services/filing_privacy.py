"""Visibility of corrections saved during a returned filing's private edit window."""

from tribunal import models as m


def returned_correction(app, created_at):
    review = m.CompletenessReview.objects.filter(
        submission__application=app, result="reject", created_at__lte=created_at
    ).order_by("-created_at", "-id").first()
    return bool(review and not app.submissions.filter(
        created_at__gt=review.created_at, created_at__lte=created_at
    ).exists())


def revision_visible(revision):
    app = revision.application
    formal = app.submissions.filter(revision=revision).exists()
    if app.status == "returned" or returned_correction(app, revision.created_at):
        return formal
    return True


def file_visible(file, *, current=False):
    attachment = file.attachment
    app = attachment.application
    if not app or attachment.owner_id != app.owner_id or attachment.report_request_id:
        return True
    submissions = app.submissions.order_by("-created_at", "-id")
    if current and app.status == "returned":
        latest = submissions.first()
        return bool(latest and any(str(file.pk) == str(item.get("id")) for item in latest.manifest))
    if app.status == "returned" or returned_correction(app, file.created_at):
        return any(str(file.pk) == str(item.get("id")) for submission in submissions for item in submission.manifest)
    return True


def audit_visible(event):
    if event.source == "tribunal.answerrevision":
        revision = m.AnswerRevision.objects.filter(pk=event.source_id).first()
        return bool(revision and revision_visible(revision))
    if event.source == "tribunal.fileversion":
        file = m.FileVersion.objects.select_related("attachment__application").filter(pk=event.source_id).first()
        return bool(file and file_visible(file))
    return True


def notice_visible(key):
    parts = key.split(":")
    if parts[0] not in {"answer_changed", "file_uploaded"}:
        return True
    if len(parts) != 3:
        return False
    from django.core.exceptions import ValidationError

    try:
        if parts[0] == "answer_changed":
            revision = m.AnswerRevision.objects.filter(pk=parts[1]).first()
            return bool(revision and revision_visible(revision))
        file = m.FileVersion.objects.select_related("attachment__application").filter(pk=parts[1]).first()
        return bool(file and file_visible(file))
    except (ValueError, ValidationError):
        return False
