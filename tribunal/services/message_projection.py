"""Actual sender display names authorized by message IDs, never Account enumeration."""
from django.db import connection
from tribunal.models import Account


def message_sender_names(messages):
    if connection.vendor == 'postgresql':
        result = {}
        for start in range(0, len(messages), 250):
            targets = [str(row.pk) for row in messages[start:start+250]]
            with connection.cursor() as cursor:
                cursor.execute('SELECT message_id,sender_name FROM public.ctm_message_sender_names(%s::uuid[])', [targets])
                result.update((str(pk), name) for pk, name in cursor.fetchall())
        return result
    senders = {str(row.pk): f'{row.first_name} {row.last_name}'.strip()
               for row in Account.objects.filter(pk__in={message.sender_id for message in messages})}
    return {str(row.pk): senders.get(str(row.sender_id)) for row in messages}
