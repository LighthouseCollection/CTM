"""Blank council print projection; never render a capability or saved response."""
from django.core.exceptions import ValidationError
from tribunal.models import ReportRequest
from tribunal.policy import staff, writer, open_proceeding


def printable_priest_request(actor, request_id):
    staff(actor)
    row = ReportRequest.objects.select_related('case', 'proceeding', 'subject').get(pk=request_id)
    writer(actor, row.case)
    open_proceeding(row.proceeding)
    if row.kind != 'external_priest' or row.state not in {'draft', 'sent'}:
        raise ValidationError('Only an unfinished external priest request can be printed.')
    # Explicit allowlist: do not pass a model instance into a template.
    return {'request_id': str(row.pk), 'title': row.title,
            'instructions': row.instructions, 'subject_name': row.subject.name,
            'priest_name': row.external_name, 'language': row.language,
            'lines': range(20)}
