"""Stripe adapter: signed callbacks, frozen candidate and recoverable finalization."""

from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction, connection
from django.db.models import Q
from django.utils import timezone
import stripe
from functools import wraps
from tribunal.models import (
    CheckoutIntent,
    FeeObligation,
    PaymentEvent,
    Application,
    Account,
    Outbox,
)
from tribunal.policy import application_for
from tribunal.policy import administrator
from .applications import (
    required_documents,
    validate_petition,
    submit_application,
    check_filing_version,
    validate_filing_declaration,
)
from .common import audit, notify, lock_key
from tribunal.validation import validate_answers, validate_attestation
from tribunal.db.context import database_actor, database_settings


def provider_event_context(command):
    @wraps(command)
    def run(event_id, payload, *args, **kwargs):
        metadata = payload.get("metadata") or {}
        reference = payload.get("payment_intent") or ""
        if isinstance(reference, dict):
            reference = reference.get("id", "")
        values = {"ctm.payment_event": str(event_id),
                  "ctm.payment_candidate": str(metadata.get("ctm_intent", "")),
                  "ctm.payment_session": str(payload.get("id", "")),
                  "ctm.payment_reference": str(reference)}
        with database_actor(None), database_settings(values):
            return command(event_id, payload, *args, **kwargs)
    return run


@transaction.atomic
def prepare_checkout(actor, app_id, attestation, *, expected_version=None):
    app = application_for(actor, app_id)
    app = (
        Application.objects.select_for_update(of=("self",))
        .select_related("questionnaire")
        .get(pk=app.pk)
    )
    if app.owner_id != actor.pk or not actor.email_verified:
        raise PermissionDenied("Only the verified filing applicant can pay.")
    check_filing_version(app, expected_version)
    if app.duplicate_hold or app.status != "draft":
        raise ValidationError("Resolve filing eligibility before payment.")
    if app.fee.status != "due":
        raise ValidationError("This fee is already satisfied.")
    validate_filing_declaration(app)
    validate_attestation(attestation)
    revision = app.revisions.filter(number=app.current_version).first()
    if not revision:
        raise ValidationError("Complete the questionnaire before paying.")
    validate_answers(app.questionnaire, revision.answers)
    if app.kind == "petition":
        validate_petition(revision.answers)
    elif not revision.answers.get("new_information"):
        raise ValidationError("Appeal requires new information/evidence.")
    from .closed_filings import require_new_information

    require_new_information(app, revision.answers)
    files = required_documents(app, revision.answers)
    manifest = [{"id": str(f.pk), "sha256": f.sha256} for f in files]
    if CheckoutIntent.objects.filter(application=app, state__in=["processing", "paid", "needs_review"]).exists():
        raise ValidationError("An existing payment requires processing or reconciliation; do not pay again.")
    existing = CheckoutIntent.objects.filter(application=app, state="pending").order_by("created_at", "id").first()
    if existing:
        if existing.revision_id != revision.pk:
            raise ValidationError("The previous checkout must expire before paying for revised answers.")
        return existing
    return CheckoutIntent.objects.create(
        application=app, revision=revision, attestation=attestation, manifest=manifest
    )


def create_checkout(actor, app_id, attestation, base_url, *, expected_version=None):
    if not settings.STRIPE_SECRET_KEY:
        raise ValidationError(
            "Payment provider is not configured; no charge was attempted."
        )
    intent = prepare_checkout(
        actor, app_id, attestation, expected_version=expected_version
    )
    stripe.api_key = settings.STRIPE_SECRET_KEY
    session = stripe.checkout.Session.create(
        mode="payment",
        client_reference_id=str(intent.pk),
        line_items=[
            {
                "price_data": {
                    "currency": "usd",
                    "unit_amount": 25000,
                    "product_data": {"name": "CTM filing fee"},
                },
                "quantity": 1,
            }
        ],
        metadata={"ctm_intent": str(intent.pk)},
        success_url=base_url + "/?payment=returned",
        cancel_url=base_url + "/?payment=cancelled",
        idempotency_key=f"ctm-checkout:{intent.pk}",
    )
    with database_settings({"ctm.checkout_created": str(intent.pk), "ctm.created_reference": session.id}), transaction.atomic():
        current = CheckoutIntent.objects.select_for_update(of=("self",)).get(
            pk=intent.pk
        )
        current.provider_reference = session.id
        current.save(update_fields=["provider_reference"])
    return {"intent": str(intent.pk), "checkout_url": session.url}


@provider_event_context
@transaction.atomic
def process_paid_checkout(event_id, session):
    """Caller verifies the provider signature; browser session is not payment authority."""
    intent = (
        CheckoutIntent.objects.select_for_update(of=("self",))
        .filter(provider_reference=session.get("id"))
        .first()
    )
    if intent is None:
        # A signed provider callback may win the race with the checkout-create response.
        candidate = session.get("metadata", {}).get("ctm_intent")
        if candidate and session.get("client_reference_id") == candidate:
            try:
                intent = (
                    CheckoutIntent.objects.select_for_update(of=("self",))
                    .filter(
                        Q(provider_reference__isnull=True) | Q(provider_reference=""),
                        pk=candidate,
                    )
                    .first()
                )
            except (ValueError, ValidationError):
                intent = None
    if (
        intent is None
        or session.get("payment_status") != "paid"
        or session.get("amount_total") != 25000
        or str(session.get("currency", "")).lower() != "usd"
    ):
        raise ValidationError("Payment does not match a valid CTM filing obligation.")
    if session.get("client_reference_id") != str(intent.pk) or session.get(
        "metadata", {}
    ).get("ctm_intent") != str(intent.pk):
        raise ValidationError(
            "Provider checkout identity does not match frozen filing."
        )
    if not intent.provider_reference:
        intent.provider_reference = session["id"]
        intent.save(update_fields=["provider_reference"])
    payment_reference = session.get("payment_intent") or ""
    if isinstance(payment_reference, dict):
        payment_reference = payment_reference.get("id", "")
    if payment_reference:
        if not isinstance(payment_reference, str) or not payment_reference.startswith("pi_"):
            raise ValidationError("Invalid provider payment identity.")
        if intent.payment_reference and intent.payment_reference != payment_reference:
            raise ValidationError("Provider payment identity changed unexpectedly.")
        intent.payment_reference = payment_reference
        intent.save(update_fields=["payment_reference"])
    fee = FeeObligation.objects.select_for_update(of=("self",)).get(
        application_id=intent.application_id
    )
    event, created = PaymentEvent.objects.get_or_create(
        provider_event_id=event_id,
        defaults={
            "application_id": intent.application_id,
            "kind": "paid",
            "amount_minor": 25000,
            "currency": "USD",
            "provider_reference": session["id"],
            "payment_reference": intent.payment_reference,
        },
    )
    if not created and (event.application_id != intent.application_id or event.provider_reference != session["id"] or event.kind != "paid"):
        raise ValidationError("Provider event identity conflicts with a recorded operation.")
    if not created or intent.state == "finalized":
        return intent
    fee.status = "paid"
    fee.save(update_fields=["status"])
    # Retain successful charge even if later validation or membership changes block finalization.
    intent.state = "paid"
    intent.save(update_fields=["state"])
    Outbox.objects.get_or_create(
        key=f"finalize:{intent.pk}",
        defaults={"kind": "finalize_payment", "payload": {"intent": str(intent.pk)}},
    )
    audit(None, "payment_verified", event)
    return intent


@provider_event_context
@transaction.atomic
def process_checkout_state(event_id, session, state):
    """Signed lifecycle facts; expiry/failure never erase a successful payment."""
    if state not in {"processing", "expired", "failed"}:
        raise ValidationError("Unsupported checkout lifecycle event.")
    candidate = session.get("metadata", {}).get("ctm_intent")
    intent = CheckoutIntent.objects.select_for_update(of=("self",)).filter(pk=candidate).first() if candidate else None
    if (intent is None or session.get("client_reference_id") != str(intent.pk)
        or (intent.provider_reference and intent.provider_reference != session.get("id"))
        or session.get("amount_total") != 25000 or str(session.get("currency", "")).lower() != "usd"):
        raise ValidationError("Lifecycle event does not match a filing checkout.")
    payment_reference = session.get("payment_intent") or ""
    if isinstance(payment_reference, dict):
        payment_reference = payment_reference.get("id", "")
    if payment_reference and (not isinstance(payment_reference, str) or not payment_reference.startswith("pi_")):
        raise ValidationError("Invalid provider payment identity.")
    event, created = PaymentEvent.objects.get_or_create(provider_event_id=event_id, defaults={
        "application_id": intent.application_id, "kind": state, "amount_minor": 25000,
        "currency": "USD", "provider_reference": session.get("id"), "payment_reference": payment_reference,
    })
    if not created and (event.application_id != intent.application_id or event.kind != state):
        raise ValidationError("Provider event identity conflicts with a recorded operation.")
    if created:
        intent.provider_reference = intent.provider_reference or session.get("id")
        if payment_reference:
            if intent.payment_reference and intent.payment_reference != payment_reference:
                raise ValidationError("Provider payment identity changed unexpectedly.")
            intent.payment_reference = payment_reference
        if intent.state in {"pending", "processing"}:
            intent.state = state
        intent.save(update_fields=["provider_reference", "payment_reference", "state"])
    return intent


@provider_event_context
@transaction.atomic
def process_finance_event(event_id, payload, kind):
    """Retain verified chargeback/refund facts; never remove the formal filing."""
    allowed = {"chargeback", "dispute_won", "dispute_lost", "dispute_warning_closed", "refunded"}
    if kind not in allowed:
        raise ValidationError("Unsupported financial event.")
    reference = payload.get("payment_intent")
    if isinstance(reference, dict):
        reference = reference.get("id")
    if not isinstance(reference, str) or not reference.startswith("pi_"):
        raise ValidationError("Financial event lacks a known provider payment identity.")
    intents = list(CheckoutIntent.objects.select_for_update(of=("self",)).filter(payment_reference=reference)[:2])
    if len(intents) != 1:
        raise ValidationError("Financial event requires payment reconciliation.")
    intent = intents[0]
    amount = payload.get("amount_refunded") if kind == "refunded" else payload.get("amount")
    if type(amount) is not int or not 0 < amount <= 25000 or str(payload.get("currency", "")).lower() != "usd":
        raise ValidationError("Financial event amount/currency requires reconciliation.")
    if not PaymentEvent.objects.filter(application_id=intent.application_id, kind="paid", provider_reference=intent.provider_reference).exists():
        raise ValidationError("Financial event arrived before the verified successful payment.")
    event, created = PaymentEvent.objects.get_or_create(provider_event_id=event_id, defaults={
        "application_id": intent.application_id, "kind": kind, "amount_minor": amount,
        "currency": "USD", "provider_reference": intent.provider_reference, "payment_reference": reference,
    })
    if not created and (event.application_id != intent.application_id or event.kind != kind or event.amount_minor != amount):
        raise ValidationError("Provider event identity conflicts with a recorded operation.")
    if created:
        audit(None, "finance_event_verified", event)
        for admin in Account.objects.filter(role__in=["admin", "secretary"], is_active=True):
            notify(admin, "payment_finance_review", event)
    return event


def finalize_paid_intent(intent_id):
    failure = None
    result = None
    with database_actor(None), database_settings({"ctm.payment_recovery": str(intent_id)}):
        try:
            result = _finalize_paid_intent(intent_id)
        except (ValidationError, PermissionDenied) as exc:
            # Commit the recoverable paid candidate and finance alerts before
            # surfacing the failure. Raising inside database_settings rolls them back.
            failure = exc
    if failure is not None:
        raise failure
    return result


def _finalize_paid_intent(intent_id):
    intent = CheckoutIntent.objects.get(pk=intent_id)
    if intent.state not in {"paid", "needs_review", "finalized"}:
        raise ValidationError("Checkout has not been paid.")
    try:
        if connection.vendor == "postgresql":
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT public.ctm_paid_filing_actor(%s)", [str(intent.pk)]
                )
                owner_id = cursor.fetchone()[0]
        else:
            owner_id = (
                intent.application.owner_id
                if intent.application.fee.status == "paid"
                and PaymentEvent.objects.filter(
                    application_id=intent.application_id,
                    kind="paid",
                    provider_reference=intent.provider_reference,
                    amount_minor=25000,
                    currency="USD",
                ).exists()
                else None
            )
        owner = Account.objects.filter(
            pk=owner_id, is_active=True, email_verified=True, role="applicant"
        ).first()
        if owner is None:
            if intent.state == "finalized":
                return None
            raise ValidationError("Paid applicant identity requires reconciliation.")
        with database_actor(owner), transaction.atomic():
            lock_key(f"person:{owner.person_id}")
            intent = CheckoutIntent.objects.select_related("revision").get(pk=intent.pk)
            if intent.state == "finalized":
                from tribunal.models import Submission

                return Submission.objects.get(
                    application_id=intent.application_id,
                    idempotency_key=f"checkout:{intent.pk}",
                )
            app = Application.objects.select_for_update(of=("self",)).get(
                pk=intent.application_id
            )
            if app.current_version != intent.revision.number:
                raise ValidationError(
                    "Answers changed after checkout; paid filing requires reconciliation."
                )
            current_ids = {
                str(f.pk) for f in required_documents(app, intent.revision.answers)
            }
            if current_ids != {f["id"] for f in intent.manifest}:
                raise ValidationError(
                    "Evidence changed after checkout; paid filing requires reconciliation."
                )
            result = submit_application(
                app.owner, app.pk, f"checkout:{intent.pk}", intent.attestation,
                paid_intent_id=intent.pk,
            )
            CheckoutIntent.objects.filter(pk=intent.pk).update(
                state="finalized", failure=""
            )
            return result
    except (ValidationError, PermissionDenied) as exc:
        CheckoutIntent.objects.filter(pk=intent.pk).update(
            state="needs_review", failure="Paid filing requires reconciliation"
        )
        for admin in Account.objects.filter(
            role__in=["admin", "secretary"], is_active=True
        ):
            notify(admin, "paid_filing_review", intent)
        raise


def application_payment_data(actor, app_id):
    app = application_for(actor, app_id)
    if actor.pk != app.owner_id:
        administrator(actor)
    fee = app.fee
    events = PaymentEvent.objects.filter(application=app).order_by("created_at", "id")
    return {"fee": {"amount_minor": fee.amount_minor, "currency": fee.currency, "status": fee.status},
            "verified_payment": events.filter(kind="paid", amount_minor=fee.amount_minor, currency=fee.currency).exists(),
            "events": [{"id": str(row.pk), "kind": row.kind, "amount_minor": row.amount_minor,
                        "amount_basis": "cumulative_refunded" if row.kind == "refunded" else "event",
                        "currency": row.currency, "timestamp": row.created_at.isoformat()} for row in events],
            "checkouts": [{"id": str(row.pk), "state": row.state, "version": row.revision.number,
                           "timestamp": row.created_at.isoformat()}
                          for row in CheckoutIntent.objects.filter(application=app).select_related("revision").order_by("created_at", "id")]}


def payment_reconciliation(actor, offset=0):
    administrator(actor)
    if not 0 <= offset <= 2**63 - 52:
        raise ValidationError("Offset is outside the supported range.")
    rows = list(CheckoutIntent.objects.filter(state__in=["paid", "needs_review"]).order_by("created_at", "id")[offset:offset+51])
    return {"items": [{"id": str(row.pk), "application_id": str(row.application_id),
                       "state": row.state, "failure": row.failure,
                       "timestamp": row.created_at.isoformat(), "can_retry": True} for row in rows[:50]],
            "next_offset": offset + 50 if len(rows) > 50 else None}


def retry_paid_filing(actor, intent_id):
    administrator(actor)
    intent = CheckoutIntent.objects.get(pk=intent_id, state__in=["paid", "needs_review", "finalized"])
    return finalize_paid_intent(intent.pk)
