"""Authorized list continuation; visibility checks precede page selection."""
from itertools import islice
from django.core.exceptions import ValidationError


def page_options(request, default_limit):
    values = {}
    for key, default in [('offset', 0), ('limit', default_limit)]:
        raw = request.GET.get(key, str(default))
        if (len(request.GET.getlist(key)) > 1 or not raw or len(raw) > 19
                or not raw.isascii() or not raw.isdecimal()):
            raise ValidationError(f'{key} must be one non-negative integer.')
        values[key] = int(raw)
    if values['offset'] > 2**63-1 or not 1 <= values['limit'] <= 250:
        raise ValidationError('Use a valid offset and a limit from1 to250.')
    return values['offset'], values['limit']


def page_records(queryset, request, *, default_limit, serialize, visible=None):
    offset, limit = page_options(request, default_limit)
    if visible is None:
        rows = list(queryset[offset:offset+limit+1])
    else:
        # Count and skip only authorized visible records. Keep at most one page
        # and a lookahead in memory; never truncate before applying privacy.
        candidates = (row for row in queryset.iterator(chunk_size=250) if visible(row))
        rows = list(islice(candidates, offset, offset+limit+1))
    return {'items': [serialize(row) for row in rows[:limit]],
            'offset': offset, 'limit': limit,
            'next_offset': offset+limit if len(rows)>limit else None}
