"""Durable, leased delivery; external I/O runs outside DB transactions."""

from celery import shared_task
from django.conf import settings
from django.core.mail import EmailMessage
from django.db import transaction, connection
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


class SupersededDelivery(Exception):
    """Obsolete job: retain explicit non-delivery instead of reporting success."""


@transaction.atomic
def claim_delivery(identifier):
    now = timezone.now()
    scope = Outbox.objects.filter(pk=identifier).values("case_id", "kind").first()
    if scope and scope["case_id"] and scope["kind"] in DIGEST_KINDS:
        lock_key(f"digest:{scope['case_id']}")
    available = Q(lease_until__isnull=True) | Q(lease_until__lte=now)
    event = (
        Outbox.objects.select_for_update(of=("self",))
        .filter(available, pk=identifier, delivered_at__isnull=True, discarded_at__isnull=True, due_at__lte=now)
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
                discarded_at__isnull=True,
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
    if event.kind in {"testimony_invited", "testimony_rescheduled", "testimony_reminder"}:
        appointment_id = event.payload.get("appointment")
        version = event.payload.get("version")
        if appointment_id is None and event.kind == "testimony_invited":
            parts = event.key.split(":")
            if len(parts) == 3 and parts[0] == "testimony_invited":
                appointment_id, version = parts[1], 1
        if connection.vendor == "postgresql":
            with connection.cursor() as cursor:
                cursor.execute("SELECT public.ctm_testimony_delivery_valid(%s,%s,%s)", [appointment_id, version, str(event.recipient_id)])
                current = cursor.fetchone()[0]
        else:
            from tribunal.models import TestimonyAppointment

            current = TestimonyAppointment.objects.filter(pk=appointment_id, version=version,
                party__account_id=event.recipient_id, agenda__session__state="planned").exclude(state="cancelled").exists()
        if not current:
            raise SupersededDelivery("Superseded testimony invitation")
    if event.kind == "message_session":
        if connection.vendor == "postgresql":
            with connection.cursor() as cursor:
                cursor.execute("SELECT public.ctm_session_delivery_closed(%s)", [event.payload.get("session")])
                closed = cursor.fetchone()[0]
        else:
            from tribunal.models import CouncilSession

            closed = CouncilSession.objects.filter(pk=event.payload.get("session"), state="closed").exists()
        if not closed:
            raise RuntimeError("Selected council session has not closed")
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
        Outbox.objects.filter(delivered_at__isnull=True, discarded_at__isnull=True, due_at__lte=timezone.now())
        .order_by("created_at")
        .values_list("pk", flat=True)[:limit]
    )
    for identifier in ids:
        events = claim_delivery(identifier)
        if not events:
            continue
        visible = []
        for item in events:
            if connection.vendor == "postgresql":
                with connection.cursor() as cursor:
                    cursor.execute("SELECT public.ctm_correction_notice_visible(%s)", [item.key])
                    permitted = cursor.fetchone()[0]
            else:
                from tribunal.services.filing_privacy import notice_visible

                permitted = notice_visible(item.key)
            if permitted:
                visible.append(item)
            else:
                Outbox.objects.filter(pk=item.pk).update(
                    discarded_at=timezone.now(), lease_until=None,
                    last_error="Private correction; no message sent",
                )
        events = visible
        if not events:
            continue
        identifiers = [event.pk for event in events]
        try:
            deliver(events)
        except SupersededDelivery:
            Outbox.objects.filter(pk__in=identifiers).update(
                discarded_at=timezone.now(), lease_until=None,
                last_error="Superseded invitation; no message sent",
            )
            continue
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
