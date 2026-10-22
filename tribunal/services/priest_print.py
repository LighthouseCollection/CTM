"""Blank council print projection; never render a capability or saved response."""
from django.core.exceptions import ValidationError
from tribunal.models import ReportRequest
from tribunal.policy import staff, writer, open_proceeding
from unicodedata import bidirectional


def text_direction(value, fallback):
    # PDF engines need an explicit first-strong direction; HTML dir=auto alone
    # is not consistently supported. Preserve all saved characters verbatim.
    for char in value:
        direction = bidirectional(char)
        if direction == 'L':
            return 'ltr'
        if direction in {'R', 'AL'}:
            return 'rtl'
    return fallback


def printable_priest_request(actor, request_id):
    staff(actor)
    row = ReportRequest.objects.select_related('case', 'proceeding', 'subject').get(pk=request_id)
    writer(actor, row.case)
    open_proceeding(row.proceeding)
    if row.kind != 'external_priest' or row.state not in {'draft', 'sent'}:
        raise ValidationError('Only an unfinished external priest request can be printed.')
    # Explicit allowlist: do not pass a model instance into a template.
    projection = {'request_id': str(row.pk), 'title': row.title,
            'instructions': row.instructions, 'subject_name': row.subject.name,
            'priest_name': row.external_name, 'language': row.language,
            'lines': range(20)}
    for key in ['title', 'instructions', 'subject_name', 'priest_name']:
        projection[key + '_direction'] = text_direction(projection[key], 'rtl' if row.language == 'ar' else 'ltr')
    return projection
