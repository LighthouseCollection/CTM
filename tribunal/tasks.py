"""Durable, leased delivery; external I/O runs outside DB transactions."""

from celery import shared_task
from django.conf import settings
from django.core.mail import EmailMessage
from django.db import transaction
from django.db.models import Q, F
from django.utils import timezone
from tribunal.models import Outbox, Case
from tribunal.services.common import lock_key

DIGEST_KINDS = {"answer_changed", "file_uploaded", "appeal_added"}
MANAGER_KINDS = DIGEST_KINDS | {
    "report_received",
    "filing_withdrawn",
    "testimony_response",
}


@transaction.atomic
def claim_delivery(identifier):
    now = timezone.now()
    scope = Outbox.objects.filter(pk=identifier).values("case_id", "kind").first()
    if scope and scope["case_id"] and scope["kind"] in DIGEST_KINDS:
        lock_key(f"digest:{scope['case_id']}")
    available = Q(lease_until__isnull=True) | Q(lease_until__lte=now)
    event = (
        Outbox.objects.select_for_update(of=("self",))
        .filter(available, pk=identifier, delivered_at__isnull=True, due_at__lte=now)
        .first()
    )
    if not event:
        return []
    ids = [event.pk]
    if event.kind in DIGEST_KINDS and event.case_id:
        ids = list(
            Outbox.objects.select_for_update(of=("self",))
            .filter(
                available,
                case_id=event.case_id,
                kind__in=DIGEST_KINDS,
                delivered_at__isnull=True,
                due_at__lte=now,
            )
            .order_by("created_at")
            .values_list("pk", flat=True)
        )
    Outbox.objects.filter(pk__in=ids).update(
        lease_until=now + timezone.timedelta(minutes=10)
    )
    return list(Outbox.objects.filter(pk__in=ids).select_related("recipient"))


def deliver(events):
    event = events[0]
    if event.kind == "finalize_payment":
        from tribunal.services.payments import finalize_paid_intent

        finalize_paid_intent(event.payload["intent"])
        return
    if event.kind == "transcribe":
        raise RuntimeError("Transcription provider not configured")
    recipient = event.recipient
    if event.kind in MANAGER_KINDS and event.case_id:
        case = Case.objects.select_related("assigned_member").get(pk=event.case_id)
        recipient = case.assigned_member
    if not recipient or not recipient.is_active:
        raise RuntimeError("Notification recipient requires review")
    if not settings.EMAIL_HOST:
        raise RuntimeError("Email provider not configured")
    message = "There is an update in your private CTM portal. Sign in at https://ctm.lighthouseway.org."
    if event.kind in DIGEST_KINDS:
        message = (
            f"{len(events)} updates were saved during the recent editing session. "
            + message
        )
    EmailMessage(
        "CTM — portal update",
        message,
        settings.DEFAULT_FROM_EMAIL,
        [recipient.email],
        headers={"Message-ID": f"<ctm-{event.pk}@ctm.lighthouseway.org>"},
    ).send(fail_silently=False)


@shared_task
def dispatch_outbox(limit=50):
    delivered = 0
    ids = list(
        Outbox.objects.filter(delivered_at__isnull=True, due_at__lte=timezone.now())
        .order_by("created_at")
        .values_list("pk", flat=True)[:limit]
    )
    for identifier in ids:
        events = claim_delivery(identifier)
        if not events:
            continue
        identifiers = [event.pk for event in events]
        try:
            deliver(events)
        except Exception:
            # Never persist provider responses, credentials or private case text as errors.
            Outbox.objects.filter(pk__in=identifiers).update(
                lease_until=None,
                attempts=F("attempts") + 1,
                due_at=timezone.now() + timezone.timedelta(minutes=2),
                last_error="Delivery/provider action failed; retained for retry",
            )
            continue
        Outbox.objects.filter(pk__in=identifiers).update(
            delivered_at=timezone.now(), lease_until=None, last_error=""
        )
        delivered += len(events)
    return delivered


@shared_task
def retention():
    from tribunal.services.retention import process_drafts

    return process_drafts()
