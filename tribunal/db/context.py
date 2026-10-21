"""Transaction-local database identity; never accepts browser supplied roles or actor IDs."""

from contextlib import contextmanager
import hashlib
from django.db import connection, transaction


@contextmanager
def database_external(request_id, token):
    """Called only after validating the external request capability; no council identity."""
    values = {
        "ctm.actor_id": "",
        "ctm.external_request": str(request_id),
        "ctm.external_digest": hashlib.sha256(token.encode()).hexdigest(),
    }
    with database_settings(values):
        yield


@contextmanager
def database_settings(values):
    if connection.vendor != "postgresql":
        yield
        return
    with transaction.atomic():
        previous = {}
        with connection.cursor() as cursor:
            for name, value in values.items():
                cursor.execute("SELECT current_setting(%s,true)", [name])
                previous[name] = cursor.fetchone()[0] or ""
                cursor.execute("SELECT set_config(%s,%s,true)", [name, value])
        try:
            yield
        finally:
            if not connection.needs_rollback:
                with connection.cursor() as cursor:
                    for name, value in previous.items():
                        cursor.execute("SELECT set_config(%s,%s,true)", [name, value])


@contextmanager
def database_actor(actor):
    actor_id = (
        str(actor.pk) if actor and actor.is_authenticated and actor.is_active else ""
    )
    with database_settings({"ctm.actor_id": actor_id}):
        yield
