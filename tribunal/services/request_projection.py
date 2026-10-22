"""Minimal request projections within existing request and council authority."""
from django.db import connection
from tribunal.models import Account


def request_author_names(requests):
    if connection.vendor == 'postgresql':
        result = {}
        for start in range(0, len(requests), 250):
            targets = [str(row.pk) for row in requests[start:start+250]]
            with connection.cursor() as cursor:
                cursor.execute('SELECT request_id,author_name FROM public.ctm_request_author_names(%s::uuid[])', [targets])
                result.update((str(pk), name) for pk, name in cursor.fetchall())
        return result
    # SQLite has no account RLS; rows have already passed the request filters.
    authors = {str(row.pk): f'{row.first_name} {row.last_name}'.strip()
               for row in Account.objects.filter(pk__in={request.author_id for request in requests})}
    return {str(row.pk): authors.get(str(row.author_id)) for row in requests}


def external_link_metadata(request, actor, *, now):
    """Council display state; never a capability or permission to bypass a command."""
    from tribunal.policy import staff, writer, open_proceeding
    from django.core.exceptions import PermissionDenied, ValidationError
    staff(actor)
    if request.kind != 'external_priest':
        return {}
    is_open = request.proceeding.status == 'open' and request.case.status == 'open'
    if request.state in {'completed', 'cancelled'}:
        state = request.state
    elif not is_open:
        state = 'closed'
    elif request.state == 'draft':
        state = 'not_issued'
    elif request.state == 'sent' and request.token_hash and request.expires_at:
        state = 'expired' if now >= request.expires_at else 'active'
    else:
        state = 'unavailable'
    can_manage = False
    try:
        writer(actor, request.case)
        open_proceeding(request.proceeding)
        can_manage = request.state in {'draft', 'sent'}
    except (PermissionDenied, ValidationError):
        pass
    return {'external_link': {
        'priest_name': request.external_name,
        'expires_at': request.expires_at.isoformat() if request.expires_at else None,
        'state': state,
        'can_issue': can_manage and request.state == 'draft',
        'can_reissue': can_manage and request.state == 'sent',
        'can_cancel': can_manage,
    }}
