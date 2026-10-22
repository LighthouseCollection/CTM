import hashlib
import secrets
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Max
from django.utils import timezone
from django.utils.crypto import constant_time_compare
from tribunal.models import (
    Proceeding,
    Party,
    ReportQuestion,
    ReportRequest,
    Report,
    ReportRevision,
    FileVersion,
    MedicalRelease,
    QuestionnaireVersion,
    Recording,
    ProcessingRun,
    TranscriptRevision,
    TranscriptReview,
)
from tribunal.policy import active, staff, writer, open_proceeding
from .common import audit, notify, notify_manager
from .applications import safe_file


@transaction.atomic
def create_request(
    actor,
    proceeding_id,
    party_id,
    kind,
    title,
    questions,
    instructions="",
    language="en",
    parent_id=None,
):
    proceeding = (
        Proceeding.objects.select_for_update(of=("self",))
        .select_related("case")
        .get(pk=proceeding_id)
    )
    writer(actor, proceeding.case)
    open_proceeding(proceeding)
    party = Party.objects.get(pk=party_id, case=proceeding.case)
    if kind not in {
        "intake",
        "interview",
        "external_priest",
        "medical",
        "psychological",
    } or language not in {"en", "ar", "both"}:
        raise ValidationError("Invalid report kind/language.")
    parent = None
    if parent_id:
        parent = Report.objects.select_related("request").get(
            pk=parent_id, request__case=proceeding.case
        )
    snapshots = []
    selected = set()
    if kind in {"intake", "interview"}:
        for question in ReportQuestion.objects.filter(foundational=True).order_by(
            "code", "-version"
        ):
            if question.code not in selected:
                snapshots.append(
                    {
                        "code": question.code,
                        "version": question.version,
                        "en": question.wording_en,
                        "ar": question.wording_ar,
                    }
                )
                selected.add(question.code)
        for item in questions:
            code = item.get("code") if isinstance(item, dict) else str(item)
            if code in selected:
                continue
            question = (
                ReportQuestion.objects.filter(code=code).order_by("-version").first()
            )
            if not question:
                raise ValidationError(
                    "Question code is not published; use an explicit custom question."
                )
            snapshots.append(
                {
                    "code": code,
                    "version": question.version,
                    "en": question.wording_en,
                    "ar": question.wording_ar,
                }
            )
            selected.add(code)
    request = ReportRequest.objects.create(
        case=proceeding.case,
        proceeding=proceeding,
        subject=party,
        author=actor,
        kind=kind,
        title=title,
        questions=snapshots,
        instructions=instructions,
        language=language,
        parent_report=parent,
    )
    audit(actor, "report_request_created", request, proceeding.case)
    return request


@transaction.atomic
def send_request(actor, request_id, external_name="", external_email=""):
    request = (
        ReportRequest.objects.select_for_update(of=("self",))
        .select_related("case", "proceeding", "subject__account")
        .get(pk=request_id)
    )
    writer(actor, request.case)
    open_proceeding(request.proceeding)
    if request.state not in {"draft", "sent"}:
        raise ValidationError("Completed/cancelled request cannot be sent.")
    for question in request.questions:
        for language in (["en", "ar"] if request.language == "both" else [request.language]):
            if not str(question.get(language, "")).strip():
                raise ValidationError("Approved question wording is missing for the selected language.")
    request.state = "sent"
    request.sent_at = timezone.now()
    token = None
    if request.kind == "external_priest":
        token = secrets.token_urlsafe(32)
        request.token_hash = hashlib.sha256(token.encode()).hexdigest()
        request.expires_at = timezone.now() + timezone.timedelta(days=30)
        request.external_name = external_name
        request.external_email = external_email
    elif request.kind != "interview" and not request.subject.account:
        raise ValidationError("Applicant must register before receiving this request.")
    request.save()
    if request.subject.account and request.kind not in {"external_priest", "interview"}:
        notify(request.subject.account, "report_requested", request, case=request.case)
    # Plain external capability is returned once to the authorized issuer, never stored in audit.
    audit(actor, "report_request_sent", request, request.case)
    return token or request


def external_request(request_id, token):
    request = ReportRequest.objects.select_related("proceeding__case", "subject").get(
        pk=request_id
    )
    if (
        request.kind != "external_priest"
        or request.state != "sent"
        or not request.expires_at
        or timezone.now() >= request.expires_at
    ):
        raise ValidationError("Report link is expired or no longer active.")
    if not constant_time_compare(
        request.token_hash, hashlib.sha256(str(token).encode()).hexdigest()
    ):
        raise PermissionDenied("Invalid report capability.")
    open_proceeding(request.proceeding)
    return request


@transaction.atomic
def complete_external(request_id, token, answers):
    ReportRequest.objects.select_for_update(of=("self",)).get(pk=request_id)
    request = external_request(request_id, token)
    if not isinstance(answers, dict) or not answers:
        raise ValidationError("Provide written testimony or a finalized recording.")
    report = Report.objects.create(request=request, method="external")
    ReportRevision.objects.create(report=report, number=1, answers=answers)
    request.state = "completed"
    request.saved_response = {}
    request.save(update_fields=["state", "saved_response"])
    notify_manager(request.case, "report_received", report)
    audit(None, "external_report_submitted", report, request.case)
    return report


@transaction.atomic
def complete_request(actor, request_id, answers, observations="", completion_date=None):
    request = (
        ReportRequest.objects.select_for_update(of=("self",))
        .select_related("case", "proceeding", "subject")
        .get(pk=request_id)
    )
    active(actor)
    open_proceeding(request.proceeding)
    if request.state != "sent" or request.kind == "external_priest":
        raise ValidationError("Request is not awaiting this response.")
    if actor.role == "applicant":
        if request.kind == "interview":
            raise PermissionDenied("Council records an in-person interview.")
        if request.subject.account_id != actor.pk:
            raise PermissionDenied("Not your request.")
        if observations:
            raise PermissionDenied(
                "Applicant cannot author internal council observations."
            )
    else:
        writer(actor, request.case)
    if request.kind in {"medical", "psychological"}:
        if not MedicalRelease.objects.filter(
            request=request, subject=request.subject.account
        ).exists():
            raise ValidationError("A signed scoped disclosure release is required.")
        file_ids = answers.get("files", [])
        if not file_ids:
            raise ValidationError("Upload the completed assessment report.")
        for file_id in file_ids:
            file = FileVersion.objects.select_related("attachment").get(pk=file_id)
            if (
                file.attachment.case_id != request.case_id
                or file.attachment.owner_id != request.subject.account_id
                or file.attachment.visibility != "medical"
                or file.attachment.report_request_id != request.pk
            ):
                raise PermissionDenied("Medical report file has wrong owner or scope.")
            if not safe_file(file):
                raise ValidationError("Await technical file validation.")
    report = Report.objects.create(
        request=request,
        author=actor,
        completion_date=completion_date or timezone.localdate(),
    )
    ReportRevision.objects.create(
        report=report, number=1, answers=answers, observations=observations, actor=actor
    )
    request.state = "completed"
    request.save(update_fields=["state"])
    notify_manager(request.case, "report_received", report)
    audit(actor, "report_submitted", report, request.case)
    return report


@transaction.atomic
def revise_report(actor, report_id, answers, observations=""):
    report = (
        Report.objects.select_for_update(of=("self",))
        .select_related("request__case", "request__proceeding")
        .get(pk=report_id)
    )
    staff(actor)
    writer(actor, report.request.case)
    open_proceeding(report.request.proceeding)
    if report.author_id != actor.pk or report.author.role == "applicant":
        raise PermissionDenied(
            "Only the original authorized council author can revise this report."
        )
    number = (report.revisions.aggregate(n=Max("number"))["n"] or 0) + 1
    revision = ReportRevision.objects.create(
        report=report,
        number=number,
        answers=answers,
        observations=observations,
        actor=actor,
    )
    audit(actor, "report_revised", revision, report.request.case)
    return revision


@transaction.atomic
def sign_medical_release(actor, request_id, file_id, scope):
    request = ReportRequest.objects.select_related(
        "subject__account", "proceeding"
    ).get(pk=request_id)
    if request.subject.account_id != actor.pk:
        raise PermissionDenied("Only the report subject can sign their release.")
    open_proceeding(request.proceeding)
    file = (
        FileVersion.objects.select_for_update(of=("self",))
        .select_related("attachment")
        .get(pk=file_id)
    )
    if (
        file.attachment.owner_id != actor.pk
        or file.attachment.case_id != request.case_id
        or file.attachment.report_request_id != request.pk
        or not safe_file(file)
    ):
        raise ValidationError(
            "A safe signature file from this subject/case is required."
        )
    definition = (
        QuestionnaireVersion.objects.filter(purpose="medical_release", published=True)
        .order_by("-number")
        .first()
    )
    if (
        not definition
        or not definition.declaration_en.strip()
        or not scope.get("council")
    ):
        raise ValidationError(
            "Approved scoped disclosure text and recipient authorization are required."
        )
    release = MedicalRelease.objects.create(
        request=request,
        subject=actor,
        declaration=definition,
        signature=file,
        scope=scope,
    )
    audit(actor, "medical_release_signed", release, request.case)
    return release


@transaction.atomic
def create_recording(
    actor, file_id, report_id=None, appointment_id=None, notice_recorded=False
):
    staff(actor)
    if bool(report_id) == bool(appointment_id):
        raise ValidationError(
            "Associate the whole recording with one report or testimony appointment."
        )
    file = (
        FileVersion.objects.select_for_update(of=("self",))
        .select_related("attachment")
        .get(pk=file_id)
    )
    if (
        file.attachment.visibility != "council"
        or not file.mime_type.startswith(("audio/", "video/"))
        or not safe_file(file)
    ):
        raise ValidationError(
            "Store a technically validated council-only recording first."
        )
    report = None
    appointment = None
    if report_id:
        report = Report.objects.select_related(
            "request__case", "request__proceeding"
        ).get(pk=report_id)
        case = report.request.case
        open_proceeding(report.request.proceeding)
        if report.request.kind in {"medical", "psychological"}:
            raise ValidationError(
                "Medical reports use their separate protected workflow."
            )
    else:
        from tribunal.models import TestimonyAppointment
        from tribunal.policy import administrator

        administrator(actor)
        appointment = TestimonyAppointment.objects.select_related("agenda__case").get(
            pk=appointment_id
        )
        case = appointment.agenda.case
        if case.status != "open" or appointment.state == "cancelled":
            raise ValidationError("Testimony is not active.")
    writer(actor, case)
    if file.attachment.case_id != case.pk:
        raise PermissionDenied("Recording belongs to another case.")
    existing = Recording.objects.filter(file=file).first()
    if existing:
        if existing.report_id != (
            report.pk if report else None
        ) or existing.appointment_id != (appointment.pk if appointment else None):
            raise ValidationError(
                "This original recording already belongs to another report or appointment."
            )
        return existing
    recording = Recording.objects.create(
        report=report,
        appointment=appointment,
        file=file,
        notice_recorded=bool(notice_recorded),
    )
    audit(actor, "recording_associated", recording, case)
    return recording


@transaction.atomic
def finalize_recording(actor, recording_id):
    recording = (
        Recording.objects.select_for_update(of=("self",))
        .select_related("report__request__proceeding", "file__attachment")
        .get(pk=recording_id)
    )
    staff(actor)
    case = recording.file.attachment.case
    writer(actor, case)
    if recording.report:
        open_proceeding(recording.report.request.proceeding)
        if recording.report.request.kind in {"medical", "psychological"}:
            raise ValidationError(
                "Medical report material cannot enter the ordinary audio API processing path."
            )
    elif case.status != "open":
        raise ValidationError(
            "Closed case cannot accept new testimony recording finalization."
        )
    if not recording.notice_recorded or not safe_file(recording.file):
        raise ValidationError("Recording notice and technical validation required.")
    if recording.finalized_at:
        return ProcessingRun.objects.get(file=recording.file, purpose="transcription")
    recording.finalized_at = timezone.now()
    recording.save(update_fields=["finalized_at"])
    run, _ = ProcessingRun.objects.get_or_create(
        file=recording.file, purpose="transcription"
    )
    from tribunal.models import Outbox

    Outbox.objects.get_or_create(
        key=f"transcribe:{run.pk}",
        defaults={"kind": "transcribe", "case": case, "payload": {"run": str(run.pk)}},
    )
    return run


@transaction.atomic
def review_transcript(actor, revision_id):
    revision = TranscriptRevision.objects.select_related(
        "recording__report__request__case"
    ).get(pk=revision_id)
    if revision.recording.report:
        case = revision.recording.report.request.case
        writer(actor, case)
    else:
        from tribunal.policy import administrator

        administrator(actor)
    record = TranscriptReview.objects.create(revision=revision, actor=actor)
    return record
