import hashlib
from django.core.exceptions import ValidationError
from django.db import connection
from django.utils import timezone
from tribunal.models import AuditEvent, Notification, Outbox


def lock_key(value):
    """Transaction-scoped serialization for cross-row invariants on PostgreSQL."""
    if connection.vendor == "postgresql":
        key = int.from_bytes(
            hashlib.sha256(str(value).encode()).digest()[:8], "big", signed=True
        )
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_xact_lock(%s)", [key])


def audit(actor, action, obj, case=None, metadata=None):
    return AuditEvent.objects.create(
        actor=actor,
        action=action,
        source=obj._meta.label_lower,
        source_id=obj.pk,
        case=case,
        metadata=metadata or {},
    )


def notify(recipient, kind, obj, case=None, payload=None, due_at=None, email=True):
    if not recipient or not recipient.is_active:
        return
    key = f"{kind}:{obj.pk}:{recipient.pk}"
    # A sender may create a notification without permission to read its recipient's
    # inbox. INSERT ON CONFLICT preserves idempotency without that read permission.
    Notification.objects.bulk_create(
        [
            Notification(
                recipient=recipient,
                key=key,
                case=case,
                kind=kind,
                payload=payload or {},
            )
        ],
        ignore_conflicts=True,
    )
    if email:
        Outbox.objects.get_or_create(
            key=key,
            defaults={
                "recipient": recipient,
                "case": case,
                "kind": kind,
                "payload": payload or {},
                "due_at": due_at or timezone.now(),
            },
        )


def notify_manager(case, kind, obj, digest=False):
    if not case or not case.assigned_member_id:
        return
    if not case.assigned_member.is_active or case.assigned_member.role == "applicant":
        from tribunal.models import Account
        for reviewer in Account.objects.filter(is_active=True, role__in=["admin", "secretary"]):
            notify(reviewer, "manager_authority_review", obj, case=case)
        return
    if digest:
        lock_key(f"digest:{case.pk}")
    due = timezone.now() + timezone.timedelta(minutes=10) if digest else None
    notify(case.assigned_member, kind, obj, case=case, due_at=due)
    if digest:
        # All unsent qualifying applicant events wait until10quiet minutes.
        Outbox.objects.filter(
            case=case,
            delivered_at__isnull=True,
            lease_until__isnull=True,
            kind__in=["answer_changed", "file_uploaded", "appeal_added"],
        ).update(due_at=due)


def latest(queryset, field="created_at"):
    value = queryset.order_by(f"-{field}", "-id").first()
    if value is None:
        raise ValidationError("Required source record is missing.")
    return value
