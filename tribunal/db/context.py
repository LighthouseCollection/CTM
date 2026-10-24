"""Transaction-local database identity; never accepts browser supplied roles or actor IDs."""

from contextlib import contextmanager
import hashlib
import uuid
from django.db import connection, transaction
from django.conf import settings
from functools import wraps
from inspect import signature


def core_operation(name, target_arg=1):
    """Scope a named server mutation; never populated from browser role claims."""
    def decorate(command):
        parameter = list(signature(command).parameters)[target_arg]
        @wraps(command)
        def run(*args, **kwargs):
            values = signature(command).bind_partial(*args, **kwargs).arguments
            target = values.get(parameter, "")
            context = {"ctm.core_operation": name, "ctm.core_target": str(getattr(target, "pk", target))}
            if name == "close":
                context["ctm.close_reason"] = str(values.get("reason", ""))
            if name == "filing":
                context["ctm.filing_created_case"] = ""
            with database_settings(context):
                return command(*args, **kwargs)
        return run
    return decorate


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
        succeeded = False
        try:
            yield
            succeeded = True
        finally:
            if succeeded and not connection.needs_rollback:
                with connection.cursor() as cursor:
                    for name, value in previous.items():
                        cursor.execute("SELECT set_config(%s,%s,true)", [name, value])


@contextmanager
def database_actor(actor):
    actor_id = (
        str(actor.pk) if actor and actor.is_authenticated and actor.is_active else ""
    )
    try:
        tribunal_id = str(uuid.UUID(str(settings.CTM_TRIBUNAL_ID)))
    except (ValueError, TypeError, AttributeError):
        tribunal_id = ""
    with database_settings({"ctm.actor_id": actor_id, "ctm.tribunal_id": tribunal_id}):
        yield
