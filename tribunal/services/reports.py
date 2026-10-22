import hashlib
import secrets
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Max, Q
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
    Recording,
    ProcessingRun,
    TranscriptRevision,
    TranscriptReview,
)
from tribunal.policy import active, staff, writer, open_proceeding
from .common import audit, notify, notify_manager
from .applications import safe_file
from .request_contracts import (ASSESSMENTS, own_request, check_request_version,
                               release_definition)


_UNBOUND = object()


def lock_request(request_id):
    # Match closure's proceeding lock before taking the individual request lock.
    proceeding_id = ReportRequest.objects.values_list("proceeding_id", flat=True).get(pk=request_id)
    Proceeding.objects.select_for_update(of=("self",)).get(pk=proceeding_id)
    return ReportRequest.objects.select_for_update(of=("self",)).select_related(
        "case", "proceeding__case", "subject__account").get(pk=request_id)


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
        if parent.request.kind in {"medical", "psychological"} and kind not in {"medical", "psychological"}:
            raise ValidationError("Assessment reports cannot be parents of ordinary follow-up requests.")
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
    request = lock_request(request_id)
    writer(actor, request.case)
    open_proceeding(request.proceeding)
    if request.state not in {"draft", "sent"}:
        raise ValidationError("Completed/cancelled request cannot be sent.")
    if request.state == "sent" and request.kind != "external_priest":
        return request
    for question in request.questions:
        for language in (["en", "ar"] if request.language == "both" else [request.language]):
            if not str(question.get(language, "")).strip():
                raise ValidationError("Approved question wording is missing for the selected language.")
    request.state = "sent"
    request.sent_at = request.sent_at or timezone.now()
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
def cancel_request(actor, request_id, expected_version):
    from .request_contracts import check_request_version
    request = lock_request(request_id)
    writer(actor, request.case)
    check_request_version(request, expected_version)
    if request.state == "cancelled":
        return request
    open_proceeding(request.proceeding)
    if request.state not in {"draft", "sent"}:
        raise ValidationError("Only an unfinished request can be cancelled.")
    request.state = "cancelled"
    request.save(update_fields=["state"])
    audit(actor, "report_request_cancelled", request, request.case)
    return request


@transaction.atomic
def complete_external(request_id, token, answers):
    lock_request(request_id)
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
def complete_request(actor, request_id, answers, observations="", completion_date=None,
                     *, expected_version=_UNBOUND):
    request = lock_request(request_id)
    active(actor)
    if actor.role == "applicant":
        own_request(actor, request)
        if observations:
            raise PermissionDenied(
                "Applicant cannot author internal council observations."
            )
    else:
        writer(actor, request.case)
    if expected_version is not _UNBOUND:
        check_request_version(request, expected_version)
    if not isinstance(answers, dict) or not answers:
        raise ValidationError("Provide a response object.")
    # An exact retry returns the original receipt, even after later closure.
    if request.state == "completed":
        report = Report.objects.filter(request=request, author=actor).first()
        original = report.revisions.filter(number=1).first() if report else None
        if (original and original.answers == answers and original.observations == observations
                and (completion_date is None or completion_date == report.completion_date)):
            return report
        raise ValidationError("A different response has already been submitted.")
    open_proceeding(request.proceeding)
    if request.state != "sent" or request.kind == "external_priest":
        raise ValidationError("Request is not awaiting this response.")
    for question in request.questions:
        value = answers.get(question["code"])
        if value is None or (isinstance(value, str) and not value.strip()) or value == []:
            raise ValidationError("Answer every requested question.")
    if request.kind in {"medical", "psychological"}:
        if not MedicalRelease.objects.filter(
            request=request, subject=request.subject.account, scope__council=True
        ).exists():
            raise ValidationError("A signed scoped disclosure release is required.")
        file_ids = answers.get("files", [])
        if not file_ids:
            raise ValidationError("Upload the completed assessment report.")
    file_ids = answers.get("files", [])
    if not isinstance(file_ids, list) or len(file_ids) != len(set(map(str, file_ids))):
        raise ValidationError("Provide distinct file identifiers as a list.")
    for file_id in file_ids:
        file = FileVersion.objects.select_related("attachment").get(pk=file_id)
        if (
            file.attachment.case_id != request.case_id
            or file.attachment.proceeding_id != request.proceeding_id
            or file.attachment.owner_id != request.subject.account_id
            or file.attachment.report_request_id != request.pk
            or file.attachment.category == "CONSENT"
            or file.attachment.visibility != ("medical" if request.kind in ASSESSMENTS else "own")
        ):
            raise PermissionDenied("Report file has wrong owner, purpose or scope.")
        if not safe_file(file) or file.attachment.versions.order_by("-number").first().pk != file.pk:
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


def require_report_disclosure(request):
    if request.kind in ASSESSMENTS and not any(
            isinstance(release.scope, dict) and release.scope.get("council") is True
            for release in MedicalRelease.objects.filter(request=request, subject=request.subject.account)):
        raise PermissionDenied("A signed scoped medical disclosure is required.")


def validate_revision_content(request, answers, observations):
    from tribunal.validation import validate_json_value
    import uuid
    if not isinstance(answers, dict) or not answers:
        raise ValidationError("Provide a response object.")
    validate_json_value(answers)
    if not isinstance(observations, str) or len(observations) > 100_000:
        raise ValidationError("Observations must be text of at most100000 characters.")
    for question in request.questions:
        value = answers.get(question["code"])
        if value is None or value == [] or (isinstance(value, str) and not value.strip()):
            raise ValidationError("Answer every requested question.")
    if request.kind in ASSESSMENTS:
        if not answers.get("files"):
            raise ValidationError("Upload the completed assessment report.")
    identifiers = answers.get("files", [])
    if not isinstance(identifiers, list) or len(identifiers) > 100:
        raise ValidationError("Provide at most100 distinct file identifiers.")
    try:
        ids = [uuid.UUID(item) for item in identifiers if isinstance(item, str)]
    except (ValueError, AttributeError):
        raise ValidationError("Provide valid file identifiers.")
    if len(ids) != len(identifiers) or len(set(ids)) != len(ids):
        raise ValidationError("Provide distinct valid file identifiers.")
    for identifier in ids:
        file = FileVersion.objects.select_related("attachment").get(pk=identifier)
        attachment = file.attachment
        if (attachment.case_id != request.case_id or attachment.proceeding_id != request.proceeding_id
                or attachment.owner_id != request.subject.account_id or attachment.report_request_id != request.pk
                or attachment.category == "CONSENT"
                or attachment.visibility != ("medical" if request.kind in ASSESSMENTS else "own")):
            raise PermissionDenied("Report file has wrong owner, purpose or scope.")
        if not safe_file(file) or attachment.versions.order_by("-number").first().pk != file.pk:
            raise ValidationError("Await technical file validation for the current source.")


@transaction.atomic
def revise_report(actor, report_id, answers, observations="", *, expected_version):
    staff(actor)
    request_id = Report.objects.values_list("request_id", flat=True).get(pk=report_id)
    proceeding_id = ReportRequest.objects.values_list("proceeding_id", flat=True).get(pk=request_id)
    # Every narrative writer and closure takes this stable lock. Do not request an
    # UPDATE lock on a closed report/request: RLS intentionally denies mutation,
    # while exact receipt recovery needs only the readable retained source.
    Proceeding.objects.select_for_update(of=("self",)).get(pk=proceeding_id)
    request = ReportRequest.objects.select_related("case", "proceeding__case", "subject__account").get(pk=request_id)
    report = (
        Report.objects
        .select_related("request__case", "request__proceeding")
        .get(pk=report_id)
    )
    writer(actor, report.request.case)
    if report.method == "paper":
        raise PermissionDenied("The paper original is retained; use a separate follow-up request.")
    if report.author_id != actor.pk or report.author.role == "applicant":
        raise PermissionDenied(
            "Only the original authorized council author can revise this report."
        )
    from tribunal.validation import validate_json_value
    import json
    if not isinstance(answers, dict) or not answers or not isinstance(observations, str) or len(observations) > 100_000:
        raise ValidationError("Provide response answers and bounded observation text.")
    validate_json_value(answers)
    require_report_disclosure(request)
    validate_json_value(observations)
    latest = report.revisions.order_by("-number").first()
    current = latest.number if latest else 0
    if type(expected_version) is not int or expected_version < 1:
        raise ValidationError("expected_version must be a positive integer.")
    # A lost acknowledgement may be recovered without changing retained content,
    # including after closure. A later/different revision cannot be replayed.
    if (latest and current == expected_version + 1 and latest.actor_id == actor.pk
            and json.dumps(latest.answers, sort_keys=True, ensure_ascii=False) == json.dumps(answers, sort_keys=True, ensure_ascii=False)
            and latest.observations == observations):
        return latest
    if expected_version != current:
        from tribunal.validation import VersionConflict
        raise VersionConflict(current)
    open_proceeding(request.proceeding)
    validate_revision_content(request, answers, observations)
    number = current + 1
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
def sign_medical_release(actor, request_id, file_id, scope, *, expected_version=_UNBOUND,
                         declaration_id=None, accepted=False):
    request = lock_request(request_id)
    own_request(actor, request)
    if expected_version is not _UNBOUND:
        check_request_version(request, expected_version)
    if request.kind not in ASSESSMENTS or request.state != "sent":
        raise ValidationError("This request is not awaiting a disclosure release.")
    open_proceeding(request.proceeding)
    if not isinstance(scope, dict) or scope != {"council": True} or scope.get("council") is not True or accepted is not True:
        raise ValidationError("Explicit acceptance and exact council recipient scope are required.")
    definition = release_definition()
    if not definition or str(definition.pk) != str(declaration_id):
        raise ValidationError("Reload the approved bilingual disclosure declaration.")
    existing = MedicalRelease.objects.filter(request=request, subject=actor).order_by("-signed_at", "-id").first()
    if existing:
        if existing.signature_id == file_id or str(existing.signature_id) == str(file_id):
            if existing.declaration_id == definition.pk and existing.scope.get("council") is True:
                return existing
        raise ValidationError("A signed release is already retained for this request.")
    file = (
        FileVersion.objects.select_for_update(of=("self",))
        .select_related("attachment")
        .get(pk=file_id)
    )
    if (
        file.attachment.owner_id != actor.pk
        or file.attachment.case_id != request.case_id
        or file.attachment.proceeding_id != request.proceeding_id
        or file.attachment.report_request_id != request.pk
        or file.attachment.category != "CONSENT"
        or file.attachment.visibility != "medical"
        or file.mime_type not in {"application/pdf", "image/png", "image/jpeg"}
        or file.attachment.versions.order_by("-number").first().pk != file.pk
        or not safe_file(file)
    ):
        raise ValidationError(
            "A safe signature file from this subject/case is required."
        )
    release = MedicalRelease.objects.create(
        request=request,
        subject=actor,
        declaration=definition,
        signature=file,
        scope={"council": True, "purpose": request.kind, "request_id": str(request.pk),
               "proceeding_id": str(request.proceeding_id)},
    )
    audit(actor, "medical_release_signed", release, request.case)
    return release


@transaction.atomic
def create_recording(
    actor, file_id, report_id=None, appointment_id=None, notice_recorded=False,
    *, duration_ms=None, recording_notice=None,
):
    staff(actor)
    import json
    if duration_ms is not None and (type(duration_ms) is not int or not 0 <= duration_ms < 2**63):
        raise ValidationError("Measured duration must be a non-negative integer or null.")
    if recording_notice is not None and (not isinstance(recording_notice, dict)
            or len(json.dumps(recording_notice)) > 10000 or recording_notice.get("acknowledged") is not True):
        raise ValidationError("Notice detail requires an explicit acknowledged boolean and bounded object.")
    if type(notice_recorded) is not bool:
        raise ValidationError("Recording notice must be an explicit boolean.")
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
    if (file.attachment.case_id != case.pk
            or (report and file.attachment.proceeding_id != report.request.proceeding_id)
            or file.attachment.report_request_id or file.attachment.application_id):
        raise PermissionDenied("Recording belongs to another case.")
    existing = Recording.objects.filter(file=file).first()
    if existing:
        if existing.report_id != (
            report.pk if report else None
        ) or existing.appointment_id != (appointment.pk if appointment else None):
            raise ValidationError(
                "This original recording already belongs to another report or appointment."
            )
        if ((duration_ms is not None and existing.duration_ms != duration_ms)
                or (recording_notice is not None and existing.recording_notice != recording_notice)):
            raise ValidationError("Recording capture facts are already retained.")
        return existing
    recording = Recording.objects.create(
        report=report,
        appointment=appointment,
        file=file,
        notice_recorded=bool(notice_recorded),
        duration_ms=duration_ms, recording_notice=recording_notice or {}, captured_by=actor,
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
    if recording.appointment_id:
        from tribunal.models import TestimonyAppointment
        appointment = TestimonyAppointment.objects.select_for_update(of=("self",)).get(pk=recording.appointment_id)
        if appointment.state == "cancelled" or appointment.agenda.case_id != case.pk:
            raise ValidationError("Recording appointment is no longer active.")
    if not recording.notice_recorded or not safe_file(recording.file):
        raise ValidationError("Recording notice and technical validation required.")
    if recording.finalized_at:
        return ProcessingRun.objects.get(file=recording.file, purpose="transcription", attempt=1)
    recording.finalized_at = timezone.now()
    recording.save(update_fields=["finalized_at"])
    run, _ = ProcessingRun.objects.get_or_create(
        file=recording.file, purpose="transcription", attempt=1
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
        "recording__report__request__case", "recording__file__attachment", "run"
    ).get(pk=revision_id)
    staff(actor)
    recording = Recording.objects.select_for_update(of=("self",)).get(pk=revision.recording_id)
    if (not recording.finalized_at or revision.run.file_id != recording.file_id
            or revision.run.purpose != "transcription" or revision.run.state != "completed"
            or not safe_file(revision.recording.file)):
        raise ValidationError("Only validated output for this finalized recording can be reviewed.")
    if revision.recording.report:
        case = revision.recording.report.request.case
        writer(actor, case)
        if revision.recording.report.request.kind in ASSESSMENTS:
            raise PermissionDenied("Assessment material cannot enter ordinary transcript review.")
    else:
        from tribunal.policy import administrator

        administrator(actor)
    if TranscriptRevision.objects.filter(recording=recording, language=revision.language,
            kind=revision.kind, number__gt=revision.number).exists():
        raise ValidationError("A newer transcript version requires review.")
    record, created = TranscriptReview.objects.get_or_create(revision=revision, actor=actor)
    if created:
        audit(actor, "transcript_reviewed", record, revision.recording.file.attachment.case)
    return record


def external_status_receipt(request_id, token):
    """No response content: a holder can inspect status but cannot reopen the link."""
    from django.db import connection
    from tribunal.db.context import database_external
    if not isinstance(token, str) or not token or len(token)>256:
        raise PermissionDenied("Invalid report capability.")
    with database_external(request_id, token):
        if connection.vendor == 'postgresql':
            with connection.cursor() as cursor:
                cursor.execute('SELECT public.ctm_external_status_receipt()')
                value = cursor.fetchone()[0]
            if value is None:
                raise PermissionDenied("Invalid report capability.")
            import json
            return json.loads(value) if isinstance(value, str) else value
        source = ReportRequest.objects.select_related('case','proceeding').get(pk=request_id)
        if (source.kind != 'external_priest' or source.proceeding.case_id != source.case_id or not source.expires_at
                or not source.token_hash or not constant_time_compare(source.token_hash, hashlib.sha256(token.encode()).hexdigest())):
            raise PermissionDenied("Invalid report capability.")
        report = Report.objects.filter(Q(method='external', author__isnull=True) | Q(method='paper'), request=source).first()
        expired = timezone.now() >= source.expires_at
        receipt = None
        if expired:
            state = 'expired'
        elif source.state == 'completed' and report:
            state = 'completed'
            receipt = {'report_id':str(report.pk), 'completed_at':report.created_at.isoformat()}
        elif source.state == 'cancelled':
            state = 'cancelled'
        elif source.state == 'closed' or source.case.status != 'open' or source.proceeding.status != 'open':
            state = 'closed'
        else:
            state = 'active' if source.state == 'sent' else 'unavailable'
        return {'state':state, 'expires_at':source.expires_at.isoformat(), 'receipt':receipt}


@transaction.atomic
def complete_external_paper(actor, request_id, file_id, completion_date, *, expected_version):
    from datetime import date
    from tribunal.db.context import database_actor, database_settings
    # The proceeding lock serializes all request writers/closure, while a plain
    # retained request read also permits exact receipt recovery after closure.
    proceeding_id = ReportRequest.objects.values_list('proceeding_id', flat=True).get(pk=request_id)
    Proceeding.objects.select_for_update(of=('self',)).get(pk=proceeding_id)
    request = ReportRequest.objects.select_related('case', 'proceeding__case').get(pk=request_id)
    writer(actor, request.case)
    check_request_version(request, expected_version)
    if request.kind != 'external_priest':
        raise ValidationError("Paper completion requires an external priest request.")
    try:
        received = date.fromisoformat(completion_date)
        if received.isoformat() != completion_date or received > timezone.localdate():
            raise ValueError
    except (ValueError, TypeError):
        raise ValidationError("Provide the received date as YYYY-MM-DD, no later than today.")
    import uuid
    try:
        file_id = uuid.UUID(str(file_id))
    except (ValueError, TypeError, AttributeError):
        raise ValidationError("Provide the paper original file ID.")
    answers = {'files': [str(file_id)]}
    if request.state == 'completed':
        report = Report.objects.filter(request=request, author=actor, method='paper', completion_date=received).first()
        if report and report.revisions.filter(number=1, answers=answers, observations='').exists():
            return report
        raise ValidationError("A different response has already been submitted.")
    open_proceeding(request.proceeding)
    if request.state != 'sent' or not request.sent_at:
        raise ValidationError("Request is not awaiting this paper response.")
    file = FileVersion.objects.select_related('attachment').get(pk=file_id)
    attachment = file.attachment
    if (attachment.report_request_id != request.pk or attachment.case_id != request.case_id
            or attachment.proceeding_id != request.proceeding_id or attachment.application_id
            or attachment.owner_id or attachment.visibility != 'council' or attachment.category != 'REPORT'
            or file.mime_type != 'application/pdf'):
        raise PermissionDenied("Paper original must be a council-only PDF bound to this request.")
    if not safe_file(file) or attachment.versions.order_by('-number').first().pk != file.pk:
        raise ValidationError("Await validation of the current paper original.")
    with database_actor(actor), database_settings({'ctm.paper_request': str(request.pk),
            'ctm.paper_file': str(file.pk), 'ctm.paper_date': received.isoformat()}):
        report = Report.objects.create(request=request, author=actor, method='paper', completion_date=received)
        ReportRevision.objects.create(report=report, number=1, answers=answers, observations='', actor=actor)
        request.state = 'completed'
        request.save(update_fields=['state'])
        notify_manager(request.case, 'report_received', report)
        audit(actor, 'external_paper_report_submitted', report, request.case)
    return report
