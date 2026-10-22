"""F12 / AS-F12: linked never-filer petition enters council queue, never reopens at payment/submission."""
from datetime import date
import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.utils import timezone
from tribunal import models as m
from tribunal.services.applications import start_application, save_answers, submit_application, waive_fee
from tribunal.services.decisions import withdraw_application, decide_appeal, add_appeal_information
from tribunal.services.council import assign_case, create_session, place_agenda, record_attendance, hear_case

pytestmark = pytest.mark.django_db
ATTESTATION = {"accepted": True, "name": "Jane Smith"}


@pytest.fixture
def closed_case(ready_application, people):
    original = ready_application
    submit_application(original.owner, original.pk, "f12-original", {"accepted": True, "name": "John Smith"})
    original.refresh_from_db()
    assign_case(people["admin"], original.case_id, people["member"].pk, people["president"].pk)
    spouse = m.Account.objects.create_user(email="f12-spouse@example.test", email_verified=True)
    party = m.Party.objects.create(case=original.case, account=spouse, person=spouse.person, slot="B", name="Jane Smith", participating=False)
    withdraw_application(original.owner, original.pk)
    original.case.refresh_from_db()
    return original, spouse, party


def prepare(spouse, case, people, *, waive=True):
    app = start_application(spouse, case.pk)
    answers = {"first_name": "Jane", "last_name": "Smith", "birth_date": "1987-04-02",
        "gender": "F", "marriage_date": "2010-05-01", "spouse_birth_date": "1985-03-14",
        "grounds": ["infidelity"], "statement": "First petition", "new_information": "New evidence for council"}
    save_answers(spouse, app.pk, answers, 0)
    for category in ["MC", "CMC", "CDD", "PHOTO"]:
        attachment = m.Attachment.objects.create(application=app, case=case, owner=spouse, category=category)
        file = m.FileVersion.objects.create(attachment=attachment, number=1, object_key=f"f12/{attachment.pk}",
            original_name="evidence.pdf", display_name="evidence.pdf", mime_type="image/jpeg" if category == "PHOTO" else "application/pdf",
            byte_count=5, sha256="d"*64, actor=spouse)
        m.FileTechnicalEvent.objects.create(file=file, task="scan", result="clean")
    if waive:
        waive_fee(people["admin"], app.pk)
    app.refresh_from_db()
    return app


def present(app, people):
    session = create_session(people["admin"], date(2031, 1, 7))
    item = place_agenda(people["member"], session.pk, app.case_id)
    record_attendance(people["admin"], session.pk, people["member"].pk, True)
    return hear_case(people["member"], item.pk)


def test_f12_first_filing_is_formal_and_queued_without_reopening(client, closed_case, people):
    from tests.test_council_contract import login
    original, spouse, party = closed_case
    login(client, spouse)
    capabilities = client.get(f"/api/cases/{original.case_id}/").json()
    assert capabilities["can_start_petition"] and capabilities["can_start_closed_intake"]
    original_name, original_reference = party.name, party.reference
    original_person = (spouse.person.first_name, spouse.person.birth_date)
    app = prepare(spouse, original.case, people)
    login(client, spouse)
    data = client.get(f"/api/applications/{app.pk}/").json()
    assert data["origin"] == "closed_case_intake" and data["requires_new_information"]
    assert data["can_submit"] and data["can_edit"]
    submission = submit_application(spouse, app.pk, "f12-first", ATTESTATION, expected_version=app.current_version)
    app.refresh_from_db(); original.case.refresh_from_db(); original.proceeding.refresh_from_db(); party.refresh_from_db()
    assert not client.get(f"/api/cases/{original.case_id}/").json()["can_start_closed_intake"]
    assert app.kind == "petition" and app.status == "submitted" and app.proceeding_id is None
    assert app.party_id == party.pk and not party.participating
    spouse.person.refresh_from_db()
    assert (party.name, party.reference) == (original_name, original_reference)
    assert (spouse.person.first_name, spouse.person.birth_date) == original_person
    assert original.case.status == original.proceeding.status == "closed"
    assert not m.OpenCaseClaim.objects.filter(case=original.case).exists()
    assert original.case.proceedings.count() == 1
    assert submission.attestation["text"] == app.questionnaire.declaration_en
    assert m.FeeObligation.objects.filter(application=app).count() == 1
    assert submit_application(spouse, app.pk, "f12-first", ATTESTATION).pk == submission.pk
    login(client, people["secretary"])
    queue = client.get("/api/applications/?state=council_consideration").json()["items"]
    assert [row["id"] for row in queue] == [str(app.pk)]
    assert not queue[0]["can_review"] and not queue[0]["can_record_result"]
    assert client.get("/api/applications/?state=awaiting_review").json()["items"] == []
    login(client, spouse)
    assert not client.get(f"/api/applications/{app.pk}/").json()["can_edit"]
    assert client.get("/api/applications/?state=council_consideration").status_code == 403


def test_f12_acceptance_reopens_same_case_and_keeps_original_locked(closed_case, people):
    original, spouse, party = closed_case
    app = prepare(spouse, original.case, people)
    submit_application(spouse, app.pk, "f12-accept", ATTESTATION)
    app.refresh_from_db()
    extra = add_appeal_information(spouse, app.pk, "Further evidence")
    hearing = present(app, people)
    result = decide_appeal(people["member"], app.pk, hearing.pk, "accept", "Council considered new information")
    original.case.refresh_from_db(); original.proceeding.refresh_from_db(); app.refresh_from_db(); party.refresh_from_db()
    assert extra.application_id == app.pk and result.reopened_proceeding.case_id == original.case_id
    assert result.reopened_proceeding_id != original.proceeding_id
    assert original.case.status == "open" and original.proceeding.status == "closed"
    assert app.status == "accepted" and app.proceeding_id is None and party.participating
    assert m.OpenCaseClaim.objects.get(person=spouse.person).case_id == original.case_id
    with pytest.raises(ValidationError):
        save_answers(spouse, app.pk, {"overwrite": True}, app.current_version)
    with pytest.raises(ValidationError):
        decide_appeal(people["member"], app.pk, hearing.pk, "accept")
    with pytest.raises(ValidationError):
        save_answers(original.owner, original.pk, {"overwrite": True}, original.current_version)


@pytest.mark.parametrize("outcome", ["decline", "withdraw"])
def test_f12_decline_or_withdraw_does_not_reopen_or_notify_other_spouse(closed_case, people, outcome):
    original, spouse, party = closed_case
    app = prepare(spouse, original.case, people)
    submit_application(spouse, app.pk, "f12-nonaccept", ATTESTATION)
    app.refresh_from_db()
    before = set(m.Notification.objects.filter(recipient=original.owner).values_list("pk", flat=True))
    if outcome == "decline":
        hearing = present(app, people)
        decide_appeal(people["member"], app.pk, hearing.pk, "decline", "Not accepted")
    else:
        withdraw_application(spouse, app.pk)
    original.case.refresh_from_db(); party.refresh_from_db()
    assert original.case.status == "closed" and original.case.proceedings.count() == 1
    assert not party.participating and not m.OpenCaseClaim.objects.filter(case=original.case).exists()
    assert set(m.Notification.objects.filter(recipient=original.owner).values_list("pk", flat=True)) == before


def test_f12_new_information_link_and_never_filing_required(closed_case, people):
    original, spouse, party = closed_case
    with pytest.raises(ValidationError):
        start_application(original.owner, original.case_id)
    stranger = m.Account.objects.create_user(email="f12-stranger@example.test", email_verified=True)
    with pytest.raises(PermissionDenied):
        start_application(stranger, original.case_id)
    app = prepare(spouse, original.case, people)
    revision = app.revisions.get(number=app.current_version)
    save_answers(spouse, app.pk, dict(revision.answers, new_information="   "), app.current_version)
    app.refresh_from_db()
    with pytest.raises(ValidationError, match="new information"):
        submit_application(spouse, app.pk, "f12-no-new", ATTESTATION)
    assert not app.submissions.exists() and m.FeeObligation.objects.get(application=app).status == "waived"


def test_f12_conflicting_open_claim_preserves_pending_filing(closed_case, people):
    original, spouse, party = closed_case
    app = prepare(spouse, original.case, people)
    submit_application(spouse, app.pk, "f12-conflict", ATTESTATION)
    app.refresh_from_db()
    other = m.Case.objects.create(number="F12-UNRELATED")
    m.OpenCaseClaim.objects.create(person=spouse.person, case=other)
    hearing = present(app, people)
    with pytest.raises(ValidationError, match="another open case"):
        decide_appeal(people["member"], app.pk, hearing.pk, "accept")
    app.refresh_from_db(); original.case.refresh_from_db(); party.refresh_from_db()
    assert app.status == "submitted" and original.case.status == "closed" and not party.participating
    assert not m.AppealDisposition.objects.filter(application=app).exists()
    assert m.OpenCaseClaim.objects.get(person=spouse.person).case_id == other.pk


def test_f12_sibling_appeal_joins_one_reopened_proceeding(closed_case, people):
    original, spouse, party = closed_case
    app = prepare(spouse, original.case, people)
    submit_application(spouse, app.pk, "f12-sibling-petition", ATTESTATION)
    appeal = start_application(original.owner, original.case_id, "appeal")
    save_answers(original.owner, appeal.pk, {"statement": "Appeal", "new_information": "Independent evidence"}, 0)
    waive_fee(people["admin"], appeal.pk)
    submit_application(original.owner, appeal.pk, "f12-sibling-appeal", {"accepted": True, "name": "John Smith"})
    hearing = present(app, people)
    first = decide_appeal(people["member"], app.pk, hearing.pk, "accept")
    second = decide_appeal(people["member"], appeal.pk, hearing.pk, "accept")
    assert first.reopened_proceeding_id == second.reopened_proceeding_id
    assert original.case.proceedings.count() == 2
    assert m.OpenCaseClaim.objects.filter(case=original.case).count() == 2
    assert not original.case.parties.filter(participating=True, withdrawn_at__isnull=False).exists()


def test_f12_accepted_first_petition_can_withdraw_without_unlocking_old_proceeding(closed_case, people):
    original, spouse, party = closed_case
    app = prepare(spouse, original.case, people)
    submit_application(spouse, app.pk, "f12-accepted-withdraw", ATTESTATION)
    hearing = present(app, people)
    disposition = decide_appeal(people["member"], app.pk, hearing.pk, "accept")
    withdraw_application(spouse, app.pk)
    original.case.refresh_from_db(); original.proceeding.refresh_from_db(); disposition.reopened_proceeding.refresh_from_db()
    assert original.case.status == original.proceeding.status == disposition.reopened_proceeding.status == "closed"
    assert m.AppealDisposition.objects.get(application=app).result == "accept"
    assert not m.OpenCaseClaim.objects.filter(case=original.case).exists()


def test_f12_paid_candidate_finalizes_without_reopening_or_allocating_another_number(closed_case, people, settings):
    from unittest.mock import patch
    from types import SimpleNamespace
    from tribunal.services.payments import create_checkout, process_paid_checkout, finalize_paid_intent
    original, spouse, party = closed_case
    app = prepare(spouse, original.case, people, waive=False)
    settings.STRIPE_SECRET_KEY = "synthetic-test-key"
    with patch("stripe.checkout.Session.create", return_value=SimpleNamespace(id="cs_f12", url="https://checkout.stripe.com/test")):
        checkout = create_checkout(spouse, app.pk, ATTESTATION, "https://test.invalid", expected_version=app.current_version)
    paid = process_paid_checkout("evt_f12", {"id": "cs_f12", "client_reference_id": checkout["intent"],
        "payment_status": "paid", "amount_total": 25000, "currency": "usd", "metadata": {"ctm_intent": checkout["intent"]}})
    result = finalize_paid_intent(paid.pk)
    app.refresh_from_db(); original.case.refresh_from_db()
    assert app.status == "submitted" and original.case.status == "closed" and app.proceeding_id is None
    assert m.Case.objects.count() == 1 and app.submissions.count() == 1
    assert m.FeeObligation.objects.get(application=app).status == "paid"
    assert m.PaymentEvent.objects.filter(application=app, kind="paid").count() == 1


@pytest.mark.django_db(transaction=True)
def test_f12_withdrawal_wins_against_waiting_council_acceptance(closed_case, people):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    from django.db import connection, connections, transaction
    if connection.vendor != "postgresql":
        pytest.skip("PostgreSQL row lock race")
    original, spouse, party = closed_case
    app = prepare(spouse, original.case, people)
    submit_application(spouse, app.pk, "f12-race", ATTESTATION)
    hearing = present(app, people)
    started = Event()

    def accept():
        try:
            actor = m.Account.objects.get(pk=people["member"].pk)
            started.set()
            return decide_appeal(actor, app.pk, hearing.pk, "accept")
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=1) as pool:
        with transaction.atomic():
            m.Application.objects.select_for_update().get(pk=app.pk)
            future = pool.submit(accept)
            assert started.wait(timeout=5)
            withdraw_application(spouse, app.pk)
        with pytest.raises(ValidationError):
            future.result(timeout=10)
    app.refresh_from_db(); original.case.refresh_from_db()
    assert app.status == "withdrawn" and original.case.status == "closed"
    assert app.submissions.count() == 1 and not m.AppealDisposition.objects.filter(application=app).exists()


def test_f12_http_result_and_staff_projection(client, closed_case, people):
    from tests.test_council_contract import login
    original, spouse, party = closed_case
    app = prepare(spouse, original.case, people)
    submit_application(spouse, app.pk, "f12-http-result", ATTESTATION)
    hearing = present(app, people)
    login(client, people["member"])
    data = client.get(f"/api/applications/{app.pk}/").json()
    assert data["can_record_result"] and any(row["id"] == str(hearing.pk) for row in data["eligible_hearings"])
    response = client.post(f"/api/applications/{app.pk}/closed-case-result/", data={"hearing_id": str(hearing.pk), "result": "accept", "explanation": "New evidence considered"}, content_type="application/json")
    assert response.status_code == 201
    data = client.get(f"/api/applications/{app.pk}/").json()
    assert not data["can_record_result"] and data["disposition"]["result"] == "accept"
    assert data["disposition"]["reopened_proceeding_id"]
    login(client, spouse)
    assert client.post(f"/api/applications/{app.pk}/closed-case-result/", data={}, content_type="application/json").status_code == 403
