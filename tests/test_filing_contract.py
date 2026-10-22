"""Applicant filing API contract and stale browser protection."""

from unittest.mock import patch
import pytest
from django.core.exceptions import ValidationError
from django.test import override_settings
from tribunal.models import (
    Account, Application, CheckoutIntent, FeeObligation, QuestionnaireVersion,
    FileTechnicalEvent, Submission,
)
from tribunal.services.applications import (
    start_application, save_answers, submit_application, review_application,
)
from tribunal.services.payments import prepare_checkout

pytestmark = pytest.mark.django_db
ATTESTATION = {"accepted": True, "name": "John Smith"}


def login(client, actor):
    client.force_login(actor, backend="allauth.account.auth_backends.AuthenticationBackend")


def post(client, app, action, **data):
    return client.post(f"/api/applications/{app.pk}/{action}/", data=data,
                       content_type="application/json")


def test_bound_questionnaire_and_filing_readiness(client, ready_application):
    app = ready_application
    login(client, app.owner)
    newer = QuestionnaireVersion.objects.create(
        purpose="petition", number=2, published=True,
        definition={"fields": [{"code": "different"}]},
        declaration_en="New declaration", declaration_ar="جديد",
    )
    data = client.get(f"/api/applications/{app.pk}/").json()
    assert data["questionnaire"] == {
        "id": str(app.questionnaire_id), "version": 1, "published": True,
        "definition": app.questionnaire.definition,
        "declaration_en": "Test declaration", "declaration_ar": "إقرار تجريبي",
    }
    assert data["questionnaire"]["id"] != str(newer.pk)
    assert data["can_edit"] and data["can_submit"]
    assert not data["can_checkout"] and not data["can_resubmit"]
    assert data["return_instructions"] == "" and not data["duplicate_hold"]
    listing = client.get("/api/applications/").json()["items"]
    assert listing[0]["questionnaire"] == data["questionnaire"]


def test_new_draft_has_no_filing_actions(client, people):
    login(client, people["applicant"])
    response = client.post("/api/applications/", data={}, content_type="application/json")
    assert response.status_code == 201
    data = response.json()
    assert data["can_edit"] and data["questionnaire"]["published"]
    assert not any(data[k] for k in ["can_submit", "can_resubmit", "can_checkout"])


def test_hold_and_unscanned_files_disable_filing(client, ready_application):
    app = ready_application
    login(client, app.owner)
    Application.objects.filter(pk=app.pk).update(duplicate_hold=True)
    data = client.get(f"/api/applications/{app.pk}/").json()
    assert data["duplicate_hold"] and not data["can_submit"]
    Application.objects.filter(pk=app.pk).update(duplicate_hold=False)
    file = app.attachments.get(category="MC").versions.first()
    FileTechnicalEvent.objects.create(file=file, task="scan", result="rejected")
    data = client.get(f"/api/applications/{app.pk}/").json()
    assert not data["can_submit"]


def test_return_keeps_signature_and_fee_and_exposes_latest_instructions(client, ready_application, people):
    app = ready_application
    original = submit_application(app.owner, app.pk, "first", ATTESTATION)
    review_application(people["secretary"], app.pk, "reject", "Correct the dates.")
    app.refresh_from_db()
    login(client, app.owner)
    data = client.get(f"/api/applications/{app.pk}/").json()
    assert data["return_instructions"] == "Correct the dates."
    assert data["can_resubmit"] and data["can_edit"]
    assert not data["can_submit"] and not data["can_checkout"]
    response = post(client, app, "submit", idempotency_key="second", expected_version=1)
    assert response.status_code == 201
    latest = app.submissions.order_by("-created_at").first()
    assert latest.attestation == {"original_submission": str(original.pk)}
    assert app.fee.status == "waived" and app.submissions.count() == 2
    review_application(people["admin"], app.pk, "reject", "Add context.")
    assert client.get(f"/api/applications/{app.pk}/").json()["return_instructions"] == "Add context."


def test_owner_projection_does_not_expose_other_or_staff_drafts(client, ready_application, people):
    app = ready_application
    other = Account.objects.create_user(email="other@example.test", email_verified=True)
    login(client, other)
    assert client.get(f"/api/applications/{app.pk}/").status_code == 403
    assert client.get("/api/applications/").json()["items"] == []
    login(client, people["admin"])
    assert client.get(f"/api/applications/{app.pk}/").status_code == 403
    submit_application(app.owner, app.pk, "submitted", ATTESTATION)
    data = client.get(f"/api/applications/{app.pk}/").json()
    assert "can_submit" not in data and "questionnaire" not in data


@pytest.mark.parametrize("value", [None, True, -1, "1", 1.0])
@pytest.mark.parametrize("action", ["submit", "checkout"])
def test_http_requires_integer_version(client, ready_application, value, action):
    app = ready_application
    login(client, app.owner)
    data = {"idempotency_key": "bad", "attestation": ATTESTATION}
    if value is not None:
        data["expected_version"] = value
    response = post(client, app, action, **data)
    assert response.status_code == 422
    assert "expected_version" in str(response.json())
    assert not CheckoutIntent.objects.exists() and not Submission.objects.exists()


def test_stale_checkout_never_contacts_provider(client, ready_application):
    app = ready_application
    FeeObligation.objects.filter(application=app).update(status="due", waived_by=None)
    login(client, app.owner)
    with override_settings(STRIPE_SECRET_KEY="test-key"), patch("stripe.checkout.Session.create") as provider:
        response = post(client, app, "checkout", attestation=ATTESTATION, expected_version=0)
    assert response.status_code == 422
    provider.assert_not_called()
    assert not CheckoutIntent.objects.exists()


def test_current_checkout_freezes_revision_without_claiming_payment(client, ready_application):
    from types import SimpleNamespace

    app = ready_application
    FeeObligation.objects.filter(application=app).update(status="due", waived_by=None)
    login(client, app.owner)
    data = client.get(f"/api/applications/{app.pk}/").json()
    assert data["can_checkout"] and not data["can_submit"]
    with override_settings(STRIPE_SECRET_KEY="test-key"), patch(
        "stripe.checkout.Session.create",
        return_value=SimpleNamespace(id="cs_unit_test", url="https://example.test/checkout"),
    ) as provider:
        response = post(client, app, "checkout", attestation=ATTESTATION, expected_version=1)
    assert response.status_code == 200
    intent = CheckoutIntent.objects.get()
    assert intent.revision.number == 1 and intent.state == "pending"
    assert response.json()["intent"] == str(intent.pk)
    assert app.fee.status == "due" and not Submission.objects.exists()
    assert provider.call_args.kwargs["idempotency_key"] == f"ctm-checkout:{intent.pk}"


def test_stale_submit_does_not_finalize_newer_answers(client, ready_application):
    app = ready_application
    answers = app.revisions.get(number=1).answers
    save_answers(app.owner, app.pk, {**answers, "statement": "Updated"}, 1)
    login(client, app.owner)
    response = post(client, app, "submit", idempotency_key="stale", attestation=ATTESTATION, expected_version=1)
    assert response.status_code == 422
    assert not Submission.objects.exists()
    response = post(client, app, "submit", idempotency_key="current", attestation=ATTESTATION, expected_version=2)
    assert response.status_code == 201
    assert Submission.objects.get().revision.number == 2
    # Idempotent replay returns the same formal submission, even after later corrections.
    save_answers(app.owner, app.pk, {**answers, "statement": "After filing"}, 2)
    response = post(client, app, "submit", idempotency_key="current", attestation=ATTESTATION, expected_version=2)
    assert response.status_code == 201 and Submission.objects.count() == 1


@pytest.mark.parametrize("declarations", [(False, "English", "العربية"), (True, "", "العربية"), (True, "English", " ")])
def test_unpublished_or_untranslated_declaration_blocks_first_filing(client, ready_application, declarations):
    app = ready_application
    published, en, ar = declarations
    questionnaire = QuestionnaireVersion.objects.create(
        purpose="petition", number=2, published=published,
        definition=app.questionnaire.definition, declaration_en=en, declaration_ar=ar,
    )
    Application.objects.filter(pk=app.pk).update(questionnaire=questionnaire)
    login(client, app.owner)
    assert not client.get(f"/api/applications/{app.pk}/").json()["can_submit"]
    with pytest.raises(ValidationError, match="bilingual"):
        submit_application(app.owner, app.pk, "invalid-declaration", ATTESTATION)
    FeeObligation.objects.filter(application=app).update(status="due", waived_by=None)
    with pytest.raises(ValidationError, match="bilingual"):
        prepare_checkout(app.owner, app.pk, ATTESTATION)
    assert not Submission.objects.exists() and not CheckoutIntent.objects.exists()


def test_closed_proceeding_disables_edit_and_resubmit(client, ready_application, people):
    from tribunal.services.decisions import record_decision, approve_decision

    app = ready_application
    submit_application(app.owner, app.pk, "closed", ATTESTATION)
    review_application(people["admin"], app.pk, "reject", "Correct dates.")
    app.refresh_from_db()
    decision = record_decision(people["admin"], app.proceeding_id, "denied", "Reason", {})
    approve_decision(people["president"], decision.pk)
    login(client, app.owner)
    data = client.get(f"/api/applications/{app.pk}/").json()
    assert not any(data[k] for k in ["can_edit", "can_submit", "can_resubmit", "can_checkout"])
