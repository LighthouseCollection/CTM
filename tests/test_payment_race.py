import pytest
from tribunal.models import FeeObligation, CheckoutIntent
from tribunal.services.payments import prepare_checkout, process_paid_checkout

pytestmark = pytest.mark.django_db


def test_signed_payment_can_arrive_before_checkout_response_saved(unpaid_application):
    app = unpaid_application
    FeeObligation.objects.filter(application=app).update(status="due", waived_by=None)
    intent = prepare_checkout(
        app.owner, app.pk, {"accepted": True, "name": "John Smith"}
    )
    assert not intent.provider_reference
    result = process_paid_checkout(
        "evt_race",
        {
            "id": "cs_race",
            "client_reference_id": str(intent.pk),
            "metadata": {"ctm_intent": str(intent.pk)},
            "amount_total": 25000,
            "currency": "usd",
            "payment_status": "paid",
        },
    )
    assert result.state == "paid"
    intent.refresh_from_db()
    assert intent.provider_reference == "cs_race"
