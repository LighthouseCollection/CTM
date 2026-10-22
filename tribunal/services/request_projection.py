"""Display names only, authorized by request identity rather than Account visibility."""
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
