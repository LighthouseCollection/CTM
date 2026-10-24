from django.http import JsonResponse
from tribunal.api import endpoint, body
from tribunal.services.priest_recording import complete_priest_recording


@endpoint(('POST',))
def complete_recording_request(request, request_id):
    data = body(request)
    if set(data) - {'file_id', 'completion_date', 'recording_notice', 'duration_ms', 'expected_version'}:
        from django.core.exceptions import ValidationError
        raise ValidationError('Unsupported recording completion fields.')
    report, recording = complete_priest_recording(request.user, request_id,
        data.get('file_id'), data.get('completion_date'), data.get('recording_notice'),
        data.get('duration_ms'), expected_version=data.get('expected_version'))
    return JsonResponse({'id': str(report.pk), 'recording_id': str(recording.pk),
                         'method': report.method, 'completion_date': report.completion_date.isoformat()}, status=201)
