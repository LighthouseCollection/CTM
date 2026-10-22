import json
import pytest
from django.core.exceptions import ValidationError
from django.test import Client, override_settings
from tribunal.models import FeeObligation, Application, FileVersion, Notification
from tribunal.services.applications import save_answers, submit_application

pytestmark = pytest.mark.django_db


def test_api_denies_anonymous_and_other_party(client, ready_application, people):
    app = ready_application
    response = client.get(f"/api/applications/{app.pk}/")
    assert response.status_code == 401
    client.force_login(
        people["member"], backend="allauth.account.auth_backends.AuthenticationBackend"
    )
    assert client.get(f"/api/applications/{app.pk}/").status_code == 403


def test_api_saves_real_revision_and_requires_csrf(people):
    client = Client(enforce_csrf_checks=True)
    client.force_login(
        people["applicant"],
        backend="allauth.account.auth_backends.AuthenticationBackend",
    )
    assert (
        client.post(
            "/api/applications/", data=json.dumps({}), content_type="application/json"
        ).status_code
        == 403
    )
    session = client.get("/api/session/")
    assert session.status_code == 200
    csrf = client.cookies["csrftoken"].value
    result = client.post(
        "/api/applications/",
        data=json.dumps({}),
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf,
    )
    assert result.status_code == 201


def test_required_configured_question_not_bypassable(ready_application, people):
    from tribunal.models import QuestionnaireVersion

    old = ready_application.questionnaire
    definition = {
        **old.definition,
        "fields": [{"code": "special", "type": "text", "required": True}],
    }
    schema = QuestionnaireVersion.objects.create(
        purpose="petition",
        number=2,
        published=True,
        definition=definition,
        declaration_en="Declaration",
        declaration_ar="إقرار",
    )
    Application.objects.filter(pk=ready_application.pk).update(questionnaire=schema)
    with pytest.raises(ValidationError):
        submit_application(
            ready_application.owner,
            ready_application.pk,
            "missing-custom",
            {"name": "John Smith", "accepted": True},
        )


def test_payment_event_wrong_amount_does_not_mark_paid(unpaid_application):
    from tribunal.services.payments import process_paid_checkout

    FeeObligation.objects.filter(application=unpaid_application).update(
        status="due", waived_by=None
    )
    with pytest.raises(ValidationError):
        process_paid_checkout(
            "evt_test",
            {
                "id": "cs_unknown",
                "amount_total": 1,
                "currency": "usd",
                "payment_status": "paid",
            },
        )
    unpaid_application.fee.refresh_from_db()
    assert unpaid_application.fee.status == "due"


def test_no_public_media_route(client):
    assert client.get("/media/originals/anything.pdf").status_code == 404


def test_closed_applicant_cannot_get_council_notes(client, ready_application, people):
    client.force_login(
        people["applicant"],
        backend="allauth.account.auth_backends.AuthenticationBackend",
    )
    assert client.get("/api/council/members/").status_code == 403


def test_one_persons_notifications_are_private(client, people):
    Notification.objects.create(
        recipient=people["admin"],
        key="x",
        kind="private",
        payload={"secret": "private"},
    )
    client.force_login(
        people["applicant"],
        backend="allauth.account.auth_backends.AuthenticationBackend",
    )
    assert client.get("/api/notifications/").json()["items"] == []
