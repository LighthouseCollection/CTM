"""Administrative queue metadata and local orphan cleanup; no private payload projection."""
import hashlib
from pathlib import Path
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import connection, transaction
from django.db.models import Case, When, Value, CharField, Q, Count
from django.utils import timezone
from tribunal.models import Outbox, FileVersion
from tribunal.policy import administrator
from tribunal.validation import VersionConflict
from .common import audit
from .files import private_path
from tribunal.db.context import core_operation


def enqueue_cleanup(key):
    return Outbox.objects.get_or_create(key="cleanup:" + hashlib.sha256(key.encode()).hexdigest(),
        defaults={"kind": "private_orphan_cleanup", "payload": {"object_key": key}})[0]


@transaction.atomic
def cleanup_orphan(event):
    key = event.payload.get("object_key") if isinstance(event.payload, dict) else None
    if not isinstance(key, str) or not key or len(key)>250:
        raise ValidationError("Cleanup source requires review.")
    candidate = Path(key)
    if candidate.is_absolute() or candidate.as_posix()!=key or any(part in {".", ".."} for part in candidate.parts):
        raise ValidationError("Cleanup requires the canonical relative storage key.")
    path = private_path(key)
    if path != Path(settings.MEDIA_ROOT).resolve()/candidate:
        raise ValidationError("Cleanup cannot follow a storage alias.")
    if connection.vendor == "postgresql":
        with connection.cursor() as cursor:
            cursor.execute("SELECT public.ctm_orphan_cleanup_allowed(%s)", [key])
            orphan = cursor.fetchone()[0]
    else:
        orphan = not FileVersion.objects.filter(object_key=key).exists()
    if not orphan:
        from tribunal.tasks import SupersededDelivery
        raise SupersededDelivery("Source still has a retained file reference")
    path.unlink(missing_ok=True)


def states():
    now = timezone.now()
    return Outbox.objects.annotate(queue_state=Case(
        When(delivered_at__isnull=False, then=Value("delivered")),
        When(discarded_at__isnull=False, then=Value("discarded")),
        When(lease_until__gt=now, then=Value("leased")),
        When(Q(attempts__gt=0) & ~Q(last_error=""), then=Value("failed")),
        default=Value("pending"), output_field=CharField()))


def queue_status(actor, *, state=None, offset=0):
    administrator(actor)
    if state is not None and state not in {"pending", "failed", "leased", "delivered", "discarded"}:
        raise ValidationError("Unsupported queue state.")
    if type(offset) is not int or not 0 <= offset <= 2**63-52:
        raise ValidationError("Invalid queue offset.")
    qs = states()
    counts = {kind: 0 for kind in ["pending", "failed", "leased", "delivered", "discarded"]}
    counts.update({row["queue_state"]: row["total"] for row in qs.values("queue_state").annotate(total=Count("pk"))})
    if state:
        qs = qs.filter(queue_state=state)
    from tribunal.tasks import EMAIL_KINDS
    known = EMAIL_KINDS | {"private_orphan_cleanup", "finalize_payment", "transcribe"}
    rows = list(qs.order_by("-created_at", "-id")[offset:offset+51])
    return {"counts": counts, "items": [{"id": str(row.pk), "kind": row.kind if row.kind in known else "unsupported",
        "state": row.queue_state, "attempts": row.attempts, "due_at": row.due_at.isoformat(),
        "created_at": row.created_at.isoformat()} for row in rows[:50]],
        "next_offset": offset+50 if len(rows)>50 else None}


@transaction.atomic
@core_operation("queue_retry")
def retry_delivery(actor, identifier, expected_attempts):
    administrator(actor)
    if type(expected_attempts) is not int or expected_attempts < 1:
        raise ValidationError("expected_attempts must be a positive integer.")
    row = Outbox.objects.select_for_update(of=("self",)).get(pk=identifier)
    if row.attempts != expected_attempts:
        raise VersionConflict(row.attempts)
    if row.delivered_at or row.discarded_at or (row.lease_until and row.lease_until>timezone.now()):
        raise ValidationError("A terminal or actively leased job cannot be retried.")
    if not row.last_error:
        return row  # The same manual retry is already pending.
    row.due_at = timezone.now()
    row.last_error = ""
    row.lease_until = None
    row.lease_token = None
    row.save(update_fields=["due_at", "last_error", "lease_until", "lease_token"])
    audit(actor, "delivery_retry_requested", row, row.case, metadata={"attempts": row.attempts})
    return row
