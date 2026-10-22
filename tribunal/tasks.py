"""Durable, leased delivery; external I/O runs outside DB transactions."""

from celery import shared_task
from django.conf import settings
from django.core.mail import EmailMessage
from django.db import transaction, connection
from django.db.models import Q, F
from django.utils import timezone
from tribunal.models import Outbox, Case
from tribunal.services.common import lock_key
import uuid
from datetime import datetime
from django.core.validators import validate_email

DIGEST_KINDS = {"answer_changed", "file_uploaded", "appeal_added"}
MANAGER_KINDS = DIGEST_KINDS | {
    "report_received",
    "filing_withdrawn",
    "testimony_response",
    "applicant_message",
}
EMAIL_KINDS = MANAGER_KINDS | {
    "assignment_changed", "decree_available", "case_reopened", "submission_received",
    "intake_submitted", "closed_intake_submitted", "report_requested", "questionnaire_updated",
    "paid_filing_review", "payment_finance_review", "manager_authority_review", "draft_expiring",
    "message", "message_session", "testimony_invited", "testimony_rescheduled", "testimony_reminder",
    "testimony_cancelled", "application_accepted", "application_returned", "petition_denied",
    "decree_issued", "petitions_withdrawn", "appeal_accept", "appeal_decline",
    "closed_intake_accept", "closed_intake_decline",
}


class SupersededDelivery(Exception):
    """Obsolete job: retain explicit non-delivery instead of reporting success."""


class DeferredDelivery(Exception):
    def __init__(self, due_at):
        self.due_at = due_at


@transaction.atomic
def claim_delivery(identifier, limit=500):
    if type(limit) is not int or not 1 <= limit <= 500:
        raise ValueError("Claim limit must be an integer from1 to500")
    now = timezone.now()
    scope = Outbox.objects.filter(pk=identifier).values("case_id", "kind").first()
    if scope and scope["case_id"] and scope["kind"] in DIGEST_KINDS:
        lock_key(f"digest:{scope['case_id']}")
    available = Q(lease_until__isnull=True) | Q(lease_until__lte=now)
    event = (
        Outbox.objects.select_for_update(of=("self",), skip_locked=True)
        .filter(available, pk=identifier, delivered_at__isnull=True, discarded_at__isnull=True, due_at__lte=now)
        .first()
    )
    if not event:
        return []
    ids = [event.pk]
    if event.kind in DIGEST_KINDS and event.case_id:
        ids = list(
            Outbox.objects.select_for_update(of=("self",), skip_locked=True)
            .filter(
                available,
                case_id=event.case_id,
                kind__in=DIGEST_KINDS,
                delivered_at__isnull=True,
                discarded_at__isnull=True,
                due_at__lte=now,
            )
            .order_by("due_at", "created_at", "id")
            .values_list("pk", flat=True)[:limit]
        )
    Outbox.objects.filter(pk__in=ids).update(
        lease_until=now + timezone.timedelta(minutes=10), lease_token=uuid.uuid4()
    )
    return list(Outbox.objects.filter(pk__in=ids))


def deliver(events):
    event = events[0]
    if event.kind == "private_orphan_cleanup":
        from tribunal.services.queue import cleanup_orphan
        cleanup_orphan(event)
        return
    if event.kind not in EMAIL_KINDS | {"finalize_payment", "transcribe"}:
        raise RuntimeError("Unsupported queue action requires review")
    if event.kind in DIGEST_KINDS and event.case_id:
        future = Outbox.objects.filter(case_id=event.case_id, kind__in=DIGEST_KINDS,
            delivered_at__isnull=True, discarded_at__isnull=True, due_at__gt=timezone.now()).order_by("-due_at").first()
        if future:
            raise DeferredDelivery(future.due_at)
    if event.kind == "draft_expiring":
        target = event.payload.get("application")
        if not target and event.key.startswith("draft-expiry:"):
            target = event.key.split(":", 2)[1]
        try:
            deadline = datetime.fromisoformat(event.payload["expires_at"])
            target = str(uuid.UUID(str(target)))
        except (KeyError, ValueError, TypeError):
            raise RuntimeError("Draft warning source requires review")
        if not timezone.is_aware(deadline):
            raise RuntimeError("Draft warning deadline requires review")
        if connection.vendor == "postgresql":
            with connection.cursor() as cursor:
                cursor.execute("SELECT public.ctm_draft_warning_current(%s,%s,%s)", [target, deadline, event.recipient_id])
                current = cursor.fetchone()[0]
        else:
            from tribunal.models import Application
            app = Application.objects.filter(pk=target, owner_id=event.recipient_id, status="draft", submitted_at__isnull=True).first()
            current = bool(app and app.last_activity+timezone.timedelta(days=180)==deadline
                and deadline>timezone.now() and not app.checkoutintent_set.exists())
        if not current:
            raise SupersededDelivery("Obsolete draft warning")
    if event.kind in {"message", "message_session"}:
        message_id = event.payload.get("message")
        if not message_id:
            raise RuntimeError("Message delivery source requires review")
        if connection.vendor == "postgresql":
            with connection.cursor() as cursor:
                cursor.execute("SELECT public.ctm_message_delivery_valid(%s,%s)", [message_id, event.recipient_id])
                valid = cursor.fetchone()[0]
        else:
            from tribunal.models import MessageRecipient
            valid = MessageRecipient.objects.filter(message_id=message_id, party__account_id=event.recipient_id,
                party__account__is_active=True, party__account__email_verified=True).exists()
        if not valid:
            raise SupersededDelivery("Message recipient is no longer authorized")
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
    if connection.vendor == "postgresql":
        from types import SimpleNamespace
        with connection.cursor() as cursor:
            cursor.execute("SELECT public.ctm_delivery_destination(%s)", [str(event.pk)])
            destination = cursor.fetchone()[0]
        if isinstance(destination, str):
            import json
            destination = json.loads(destination)
        recipient = SimpleNamespace(**destination) if destination else None
    else:
        recipient = event.recipient
        if event.kind in MANAGER_KINDS and event.case_id:
            recipient = Case.objects.select_related("assigned_member").get(pk=event.case_id).assigned_member
    if event.kind in MANAGER_KINDS and event.case_id:
        if recipient and recipient.role == "applicant":
            raise RuntimeError("Current manager authority requires review")
    if not recipient or not recipient.is_active or not recipient.email_verified:
        raise RuntimeError("Notification recipient requires review")
    validate_email(recipient.email)
    if not settings.EMAIL_HOST:
        raise RuntimeError("Email provider not configured")
    message = "There is an update in your private CTM portal. Sign in at https://ctm.lighthouseway.org."
    if event.kind in DIGEST_KINDS:
        message = (
            f"{len(events)} updates were saved during the recent editing session. "
            + message
        )
    accepted = EmailMessage(
        "CTM — portal update",
        message,
        settings.DEFAULT_FROM_EMAIL,
        [recipient.email],
        headers={"Message-ID": f"<ctm-{event.pk}@ctm.lighthouseway.org>"},
    ).send(fail_silently=False)
    if type(accepted) is not int or accepted != 1:
        raise RuntimeError("Email backend did not acknowledge delivery")


@shared_task
def dispatch_outbox(limit=50):
    if type(limit) is not int or not 1 <= limit <= 500:
        raise ValueError("Delivery batch limit must be an integer from1 to500")
    delivered = 0
    claimed = 0
    now = timezone.now()
    ids = list(
        Outbox.objects.filter(Q(lease_until__isnull=True) | Q(lease_until__lte=now),
            delivered_at__isnull=True, discarded_at__isnull=True, due_at__lte=now)
        .order_by("due_at", "created_at", "id")
        .values_list("pk", flat=True)[:limit]
    )
    for identifier in ids:
        if claimed >= limit:
            break
        events = claim_delivery(identifier, limit=limit-claimed)
        claimed += len(events)
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
                Outbox.objects.filter(pk=item.pk, lease_token=item.lease_token).update(
                    discarded_at=timezone.now(), lease_until=None, lease_token=None,
                    last_error="Private correction; no message sent",
                )
        events = visible
        if not events:
            continue
        identifiers = [event.pk for event in events]
        token = events[0].lease_token
        owned = Outbox.objects.filter(pk__in=identifiers, lease_token=token,
            lease_until__gt=timezone.now(), delivered_at__isnull=True, discarded_at__isnull=True)
        if owned.count() != len(identifiers):
            continue
        try:
            deliver(events)
        except DeferredDelivery as deferred:
            Outbox.objects.filter(pk__in=identifiers, lease_token=token).update(
                lease_until=None, lease_token=None, due_at=deferred.due_at)
            continue
        except SupersededDelivery:
            Outbox.objects.filter(pk__in=identifiers, lease_token=token).update(
                discarded_at=timezone.now(), lease_until=None,
                lease_token=None, last_error="Superseded source or recipient; no message sent",
            )
            continue
        except Exception:
            # Never persist provider responses, credentials or private case text as errors.
            Outbox.objects.filter(pk__in=identifiers, lease_token=token).update(
                lease_until=None, lease_token=None,
                attempts=F("attempts") + 1,
                due_at=timezone.now() + timezone.timedelta(minutes=min(120, 2**min(7, events[0].attempts+1))),
                last_error="Delivery/provider action failed; retained for retry",
            )
            continue
        delivered += Outbox.objects.filter(pk__in=identifiers, lease_token=token).update(
            delivered_at=timezone.now(), lease_until=None, lease_token=None, last_error=""
        )
    return delivered


@shared_task
def retention():
    from tribunal.services.retention import process_drafts

    return process_drafts()
