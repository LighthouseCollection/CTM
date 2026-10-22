import hashlib
import hmac
import json
import time
import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import override_settings
from tribunal.models import CheckoutIntent, FeeObligation, PaymentEvent, Notification, Submission
from tribunal.services.applications import save_answers, submit_application, waive_fee
from tribunal.services.payments import (
    prepare_checkout, process_paid_checkout, process_checkout_state, process_finance_event,
    finalize_paid_intent, application_payment_data, payment_reconciliation, retry_paid_filing,
)

pytestmark = pytest.mark.django_db
ATTESTATION = {"accepted": True, "name": "John Smith"}


@pytest.fixture
def checkout(unpaid_application):
    app = unpaid_application
    intent = prepare_checkout(app.owner, app.pk, ATTESTATION)
    payload = {"id": "cs_lifecycle", "client_reference_id": str(intent.pk),
               "metadata": {"ctm_intent": str(intent.pk)}, "amount_total": 25000,
               "currency": "usd", "payment_status": "paid", "payment_intent": "pi_lifecycle"}
    return app, intent, payload


def signed_post(client, event_type, payload, event_id="evt_lifecycle"):
    body = json.dumps({"id": event_id, "object": "event", "type": event_type, "data": {"object": payload}})
    timestamp = str(int(time.time()))
    secret = "whsec_lifecycle_test_only"
    digest = hmac.new(secret.encode(), f"{timestamp}.{body}".encode(), hashlib.sha256).hexdigest()
    with override_settings(STRIPE_WEBHOOK_SECRET=secret):
        return client.post("/integrations/stripe/", data=body, content_type="application/json",
                           HTTP_STRIPE_SIGNATURE=f"t={timestamp},v1={digest}")


def test_unpaid_completion_waits_for_actual_success(client, checkout):
    app, intent, payload = checkout
    response = signed_post(client, "checkout.session.completed", {**payload, "payment_status": "unpaid"})
    assert response.status_code == 200 and response.json()["payment_pending"]
    intent.refresh_from_db()
    assert intent.state == "processing" and app.fee.status == "due"
    assert not Submission.objects.exists()
    with pytest.raises(ValidationError, match="do not pay again"):
        prepare_checkout(app.owner, app.pk, ATTESTATION)
    response = signed_post(client, "checkout.session.async_payment_succeeded", payload, "evt_actual_paid")
    assert response.status_code == 200
    app.refresh_from_db()
    assert app.status == "submitted" and app.submissions.count() == 1


@pytest.mark.parametrize("terminal", ["expired", "failed"])
def test_terminal_events_are_idempotent_and_allow_new_attempt(checkout, terminal):
    app, intent, payload = checkout
    process_checkout_state("evt_terminal", payload, terminal)
    process_checkout_state("evt_terminal", payload, terminal)
    assert PaymentEvent.objects.count() == 1
    next_intent = prepare_checkout(app.owner, app.pk, ATTESTATION)
    assert next_intent.pk != intent.pk
    assert app.fee.status == "due" and not Submission.objects.exists()


def test_late_expiry_does_not_downgrade_paid_filing(checkout):
    app, intent, payload = checkout
    process_paid_checkout("evt_paid", payload)
    result = finalize_paid_intent(intent.pk)
    process_checkout_state("evt_expired_late", payload, "expired")
    intent.refresh_from_db()
    assert intent.state == "finalized" and Submission.objects.get().pk == result.pk


def test_stale_pending_checkout_prevents_a_second_charge_and_waiver(checkout, people):
    app, intent, _ = checkout
    answers = app.revisions.get(number=1).answers
    save_answers(app.owner, app.pk, {**answers, "statement": "New"}, 1)
    with pytest.raises(ValidationError, match="previous checkout"):
        prepare_checkout(app.owner, app.pk, ATTESTATION)
    with pytest.raises(ValidationError, match="unresolved checkout"):
        waive_fee(people["admin"], app.pk)
    assert CheckoutIntent.objects.count() == 1


@pytest.mark.parametrize("kind", ["chargeback", "dispute_won", "dispute_lost", "refunded"])
def test_chargebacks_and_refunds_retain_submission_and_notify_finance(checkout, people, kind):
    app, intent, payload = checkout
    process_paid_checkout("evt_paid", payload)
    submitted = finalize_paid_intent(intent.pk)
    event_payload = {"payment_intent": "pi_lifecycle", "amount": 25000, "amount_refunded": 25000, "currency": "usd"}
    event = process_finance_event("evt_financial", event_payload, kind)
    process_finance_event("evt_financial", event_payload, kind)
    assert app.submissions.get().pk == submitted.pk
    assert set(Notification.objects.filter(kind="payment_finance_review").values_list("recipient_id", flat=True)) == {people["admin"].pk, people["secretary"].pk}
    assert PaymentEvent.objects.filter(pk=event.pk, kind=kind).count() == 1
    app.fee.refresh_from_db()
    assert app.fee.status == "paid"


def test_unknown_or_wrong_financial_event_is_not_acknowledged(client, checkout):
    _, _, payload = checkout
    process_paid_checkout("evt_paid", payload)
    response = signed_post(client, "charge.dispute.created", {
        "payment_intent": "pi_unknown", "amount": 25000, "currency": "usd"})
    assert response.status_code == 503
    assert not PaymentEvent.objects.filter(kind="chargeback").exists()


def test_conflicting_provider_event_id_cannot_be_reused(checkout):
    _, _, payload = checkout
    process_checkout_state("evt_conflict", payload, "processing")
    with pytest.raises(ValidationError, match="conflicts"):
        process_paid_checkout("evt_conflict", payload)


def test_paid_candidate_cannot_be_submitted_via_browser_bypass(checkout):
    app, intent, payload = checkout
    process_paid_checkout("evt_paid", payload)
    with pytest.raises(ValidationError, match="existing checkout"):
        submit_application(app.owner, app.pk, f"checkout:{intent.pk}", ATTESTATION)
    assert not Submission.objects.exists()
    assert finalize_paid_intent(intent.pk).application_id == app.pk


def test_own_payment_history_and_reconciliation_are_not_payment_simulation(checkout, people):
    app, intent, payload = checkout
    data = application_payment_data(app.owner, app.pk)
    assert not data["verified_payment"] and data["fee"]["status"] == "due"
    process_paid_checkout("evt_paid", payload)
    data = application_payment_data(app.owner, app.pk)
    assert data["verified_payment"] and data["events"][0]["kind"] == "paid"
    assert "payment_reference" not in json.dumps(data)
    assert payment_reconciliation(people["admin"])["items"][0]["id"] == str(intent.pk)
    with pytest.raises(PermissionDenied):
        payment_reconciliation(app.owner)
    result = retry_paid_filing(people["secretary"], intent.pk)
    assert result.application_id == app.pk
    assert retry_paid_filing(people["secretary"], intent.pk).pk == result.pk
    assert not payment_reconciliation(people["admin"])["items"]


def test_waiver_is_not_a_provider_payment(ready_application):
    app = ready_application
    data = application_payment_data(app.owner, app.pk)
    assert data["fee"]["status"] == "waived" and not data["verified_payment"] and not data["events"]


def test_late_paid_old_candidate_survives_new_attempt_as_reconciliation(checkout, people):
    app, old, payload = checkout
    process_checkout_state("evt_old_expired", payload, "expired")
    current = prepare_checkout(app.owner, app.pk, ATTESTATION)
    assert current.pk != old.pk
    process_paid_checkout("evt_late_success", payload)
    with pytest.raises(ValidationError, match="existing checkout"):
        finalize_paid_intent(old.pk)
    old.refresh_from_db()
    assert old.state == "needs_review" and not Submission.objects.exists()
    assert PaymentEvent.objects.filter(provider_event_id="evt_late_success", kind="paid").exists()
    assert payment_reconciliation(people["admin"])["items"][0]["id"] == str(old.pk)
