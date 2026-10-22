"""Council-recorded source completion, distinct from priest-authored narrative."""
from datetime import date
import json
import uuid
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone
from tribunal import models as m
from tribunal.db.context import database_actor, database_settings
from tribunal.policy import writer, open_proceeding
from tribunal.validation import validate_json_value
from .applications import safe_file
from .common import audit, notify_manager
from .request_contracts import check_request_version
from .reports import create_recording, finalize_recording


@transaction.atomic
def complete_priest_recording(actor, request_id, file_id, completion_date,
                              recording_notice, duration_ms=None, *, expected_version):
    proceeding_id = m.ReportRequest.objects.values_list('proceeding_id', flat=True).get(pk=request_id)
    m.Proceeding.objects.select_for_update(of=('self',)).get(pk=proceeding_id)
    request = m.ReportRequest.objects.select_related('case', 'proceeding__case').get(pk=request_id)
    writer(actor, request.case)
    check_request_version(request, expected_version)
    if request.kind != 'external_priest':
        raise ValidationError('Recording completion requires an external priest request.')
    try:
        received = date.fromisoformat(completion_date)
        if received.isoformat() != completion_date or received > timezone.localdate():
            raise ValueError
        file_id = uuid.UUID(str(file_id))
    except (ValueError, TypeError, AttributeError):
        raise ValidationError('Provide the recording file UUID and a received date no later than today.')
    validate_json_value(recording_notice, maximum=10000)
    if (not isinstance(recording_notice, dict) or recording_notice.get('acknowledged') is not True
            or len(json.dumps(recording_notice)) > 10000):
        raise ValidationError('Record an explicit, bounded acknowledgement that the person was informed of recording.')
    if duration_ms is not None and (type(duration_ms) is not int or not 0 <= duration_ms < 2**63):
        raise ValidationError('Measured duration must be a non-negative integer or null.')
    answers = {'files': [str(file_id)]}
    if request.state == 'completed':
        report = m.Report.objects.filter(request=request, author=actor, method='recording', completion_date=received).first()
        recording = m.Recording.objects.filter(report=report, file_id=file_id,
            captured_by=actor, notice_recorded=True, recording_notice=recording_notice,
            duration_ms=duration_ms, finalized_at__isnull=False).first() if report else None
        if recording and report.revisions.filter(number=1, answers=answers, observations='').exists():
            return report, recording
        raise ValidationError('A different response has already been submitted.')
    open_proceeding(request.proceeding)
    if request.state != 'sent' or not request.sent_at:
        raise ValidationError('Request is not awaiting this recorded response.')
    file = m.FileVersion.objects.select_related('attachment').get(pk=file_id)
    attachment = file.attachment
    if (attachment.case_id != request.case_id or attachment.proceeding_id != request.proceeding_id
            or attachment.owner_id or attachment.application_id or attachment.report_request_id
            or attachment.visibility != 'council' or attachment.category != 'AUDIO'
            or not file.mime_type.startswith(('audio/', 'video/'))):
        raise PermissionDenied('Use a council-only recording original for this case and proceeding.')
    if (not safe_file(file) or attachment.versions.order_by('-number').first().pk != file.pk
            or m.Recording.objects.filter(file=file).exists()):
        raise ValidationError('Use a validated current original not already associated with another recording.')
    with database_actor(actor), database_settings({'ctm.recording_request': str(request.pk),
            'ctm.recording_file': str(file.pk), 'ctm.recording_date': received.isoformat(),
            'ctm.recording_acknowledged': 'true'}):
        report = m.Report.objects.create(request=request, author=actor, method='recording', completion_date=received)
        m.ReportRevision.objects.create(report=report, number=1, answers=answers, observations='', actor=actor)
        recording = create_recording(actor, file.pk, report_id=report.pk, notice_recorded=True,
                                     duration_ms=duration_ms, recording_notice=recording_notice)
        finalize_recording(actor, recording.pk)
        recording.refresh_from_db()
        request.state = 'completed'
        request.save(update_fields=['state'])
        notify_manager(request.case, 'report_received', report)
        audit(actor, 'external_recording_report_submitted', report, request.case)
    return report, recording
