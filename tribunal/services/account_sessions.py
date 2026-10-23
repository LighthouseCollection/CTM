"""Own Django-session administration; opaque handles are never login credentials."""
import re
from django.conf import settings
from django.contrib.sessions.models import Session
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.utils import timezone
from django.utils.crypto import constant_time_compare, salted_hmac
from tribunal.db.context import database_actor
from tribunal.models import Account
from tribunal.policy import active
from .common import audit


def session_handle(actor, key):
    return salted_hmac(
        'ctm.own-session-handle.v1', f'{actor.pk}:{key}', algorithm='sha256'
    ).hexdigest()


def owned_session(actor, row):
    data = row.get_decoded()
    if (data.get('_auth_user_id') != str(actor.pk)
            or data.get('_auth_user_backend') not in settings.AUTHENTICATION_BACKENDS):
        return False
    value = data.get('_auth_user_hash')
    if not isinstance(value, str) or not value:
        return False
    return any(constant_time_compare(value, expected) for expected in (
        actor.get_session_auth_hash(), *actor.get_session_auth_fallback_hash()
    ))


def active_sessions():
    return Session.objects.filter(expire_date__gt=timezone.now()).order_by('-expire_date', 'session_key')


@transaction.atomic
def revoke_session(actor, handle, current_key):
    active(actor)
    if not re.fullmatch('[0-9a-f]{64}', handle):
        raise ObjectDoesNotExist
    with database_actor(actor):
        # Serialize with account suspension and recheck current account authority.
        account = Account.objects.select_for_update().get(pk=actor.pk)
        active(account)
        for candidate in active_sessions().iterator(chunk_size=250):
            if not constant_time_compare(session_handle(account, candidate.session_key), handle):
                continue
            row = Session.objects.select_for_update().filter(
                session_key=candidate.session_key, expire_date__gt=timezone.now()
            ).first()
            if row is None or not owned_session(account, row):
                break
            current = row.session_key == current_key
            row.delete()
            audit(account, 'account_session_revoked', account,
                  metadata={'session_handle': handle, 'current_session': current})
            return {'revoked': True, 'current_session': current}
    raise ObjectDoesNotExist
