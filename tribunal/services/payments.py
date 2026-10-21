"""Stripe adapter: signed callbacks, frozen candidate and recoverable finalization."""

from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction, connection
from django.db.models import Q
from django.utils import timezone
import stripe
from tribunal.models import (
    CheckoutIntent,
    FeeObligation,
    PaymentEvent,
    Application,
    Account,
    Outbox,
)
from tribunal.policy import application_for
from .applications import required_documents, validate_petition, submit_application
from .common import audit, notify, lock_key
from tribunal.validation import validate_answers, validate_attestation
from tribunal.db.context import database_actor


@transaction.atomic
def prepare_checkout(actor, app_id, attestation):
    app = application_for(actor, app_id)
    app = (
        Application.objects.select_for_update(of=("self",))
        .select_related("questionnaire")
        .get(pk=app.pk)
    )
    if app.owner_id != actor.pk or not actor.email_verified:
        raise PermissionDenied("Only the verified filing applicant can pay.")
    if app.duplicate_hold or app.status != "draft":
        raise ValidationError("Resolve filing eligibility before payment.")
    if app.fee.status != "due":
        raise ValidationError("This fee is already satisfied.")
    validate_attestation(attestation)
    revision = app.revisions.filter(number=app.current_version).first()
    if not revision:
        raise ValidationError("Complete the questionnaire before paying.")
    validate_answers(app.questionnaire, revision.answers)
    if app.kind == "petition":
        validate_petition(revision.answers)
    elif not revision.answers.get("new_information"):
        raise ValidationError("Appeal requires new information/evidence.")
    files = required_documents(app, revision.answers)
    manifest = [{"id": str(f.pk), "sha256": f.sha256} for f in files]
    existing = CheckoutIntent.objects.filter(
        application=app, revision=revision, state="pending"
    ).first()
    if existing:
        return existing
    return CheckoutIntent.objects.create(
        application=app, revision=revision, attestation=attestation, manifest=manifest
    )


def create_checkout(actor, app_id, attestation, base_url):
    if not settings.STRIPE_SECRET_KEY:
        raise ValidationError(
            "Payment provider is not configured; no charge was attempted."
        )
    intent = prepare_checkout(actor, app_id, attestation)
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
    with transaction.atomic():
        current = CheckoutIntent.objects.select_for_update(of=("self",)).get(
            pk=intent.pk
        )
        current.provider_reference = session.id
        current.save(update_fields=["provider_reference"])
    return {"intent": str(intent.pk), "checkout_url": session.url}


@database_actor(None)
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
        },
    )
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


def finalize_paid_intent(intent_id):
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
                app.owner, app.pk, f"checkout:{intent.pk}", intent.attestation
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
