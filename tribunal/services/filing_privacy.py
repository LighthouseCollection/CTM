"""Visibility of corrections saved during a returned filing's private edit window."""

from django.db.models import BooleanField, Case, Exists, F, OuterRef, Q, Subquery, Value, When

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


def council_revision(app):
    """The revision anyone but the filer may read (SEC-312-2): the current one when
    revision_visible, otherwise the latest formal submission's revision, or None.
    Not keyed on status == "returned": a corrected returned filing can be withdrawn
    and its current_version is still the private correction (SEC-312-2a)."""
    revision = app.revisions.filter(number=app.current_version).first()
    if revision is not None and revision_visible(revision):
        return revision
    formal = app.submissions.select_related("revision").order_by("-created_at", "-id").first()
    return formal.revision if formal else None


def _ground_answers_q(values):
    """SQL form of applications.submitted_grounds(answers) holding any of values:
    answers.grounds (a list or one string), else answers.reason when grounds is empty."""
    has_grounds = ~(Q(answers__grounds__isnull=True) | Q(answers__grounds=None) | Q(answers__grounds=[])
                    | Q(answers__grounds="") | Q(answers__grounds=False))
    match = Q()
    for value in values:
        match |= (has_grounds & (Q(answers__grounds__contains=[value]) | Q(answers__grounds=value))) | (
            ~has_grounds & (Q(answers__reason__contains=[value]) | Q(answers__reason=value)))
    return match


def council_revision_answers_q(values):
    """A Q on Application: its council_revision(app) answers select one of the ground values.

    The same rule as council_revision in one query. The current revision R is visible
    when it is a formal submission, or the filing is not returned and R is not a
    correction saved after the latest rejection with no submission since."""
    app = OuterRef("application_id")
    current = m.AnswerRevision.objects.filter(application=app, number=OuterRef("_version"))
    revisions = (
        m.AnswerRevision.objects.filter(application=OuterRef("pk"))
        .annotate(_version=F("application__current_version"), _status=F("application__status"))
        .annotate(
            _current_pk=Subquery(current.values("pk")[:1]),
            _current_at=Subquery(current.values("created_at")[:1]),
            _formal_pk=Subquery(m.Submission.objects.filter(application=app)
                                .order_by("-created_at", "-id").values("revision_id")[:1]),
        )
        .annotate(_last_reject=Subquery(
            m.CompletenessReview.objects.filter(
                submission__application=app, result="reject", created_at__lte=OuterRef("_current_at"))
            .order_by("-created_at", "-id").values("created_at")[:1]))
        .annotate(_current_visible=Case(When(
            Q(_current_pk__isnull=False) & (
                Exists(m.Submission.objects.filter(application=app, revision=OuterRef("_current_pk")))
                | (~Q(_status="returned") & (
                    Q(_last_reject__isnull=True)
                    | Exists(m.Submission.objects.filter(
                        application=app, created_at__gt=OuterRef("_last_reject"),
                        created_at__lte=OuterRef("_current_at")))))),
            then=Value(True)), default=Value(False), output_field=BooleanField()))
        .filter((Q(_current_visible=True) & Q(pk=F("_current_pk")))
                | (Q(_current_visible=False) & Q(pk=F("_formal_pk"))))
        .filter(_ground_answers_q(values))
    )
    return Q(Exists(revisions))


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
