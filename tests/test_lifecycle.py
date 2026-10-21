import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from tribunal.models import *
from tribunal.services.applications import (
    submit_application,
    save_answers,
    review_application,
    start_application,
)

pytestmark = pytest.mark.django_db


def submit(app, key="first"):
    return submit_application(
        app.owner, app.pk, key, {"accepted": True, "name": "John Smith"}
    )


def test_submission_return_and_resubmit_keep_case_fee_and_history(
    ready_application, people
):
    app = ready_application
    original = submit(app)
    app.refresh_from_db()
    number = app.case.number
    review_application(people["secretary"], app.pk, "reject", "Clarify the statement")
    save_answers(
        app.owner, app.pk, {**original.revision.answers, "statement": "Clarified"}, 1
    )
    again = submit_application(app.owner, app.pk, "second")
    app.refresh_from_db()
    assert app.case.number == number
    assert app.submissions.count() == 2
    assert original.revision.answers["statement"] == "Statement"
    assert app.fee.status == "waived"
    assert again.attestation["original_submission"] == str(original.pk)


def test_double_submit_idempotent_and_next_draft_blocked(ready_application):
    original = submit(ready_application)
    assert submit(ready_application).pk == original.pk
    with pytest.raises(ValidationError):
        start_application(ready_application.owner)


def test_only_president_authorized_assignment(ready_application, people):
    from tribunal.services.council import assign_case

    submit(ready_application)
    ready_application.refresh_from_db()
    with pytest.raises(PermissionDenied):
        assign_case(
            people["member"],
            ready_application.case.pk,
            people["member"].pk,
            people["president"].pk,
        )


def test_only_original_author_edits_note(ready_application, people):
    from tribunal.services.council import assign_case, save_note

    submit(ready_application)
    ready_application.refresh_from_db()
    case = ready_application.case
    assign_case(people["admin"], case.pk, people["member"].pk, people["president"].pk)
    note = save_note(people["member"], ready_application.proceeding.pk, "Private note")
    with pytest.raises(PermissionDenied):
        save_note(
            people["admin"], ready_application.proceeding.pk, "Overwrite", note.pk
        )


def test_decision_approval_does_not_transfer_to_revision(ready_application, people):
    from tribunal.services.council import assign_case
    from tribunal.services.decisions import record_decision, approve_decision

    submit(ready_application)
    ready_application.refresh_from_db()
    case = ready_application.case
    assign_case(people["admin"], case.pk, people["member"].pk, people["president"].pk)
    first = record_decision(
        people["member"],
        ready_application.proceeding.pk,
        "diss-applicant",
        "Reason",
        {str(ready_application.party_id): "certificate"},
    )
    approve_decision(people["president"], first.pk)
    second = record_decision(
        people["member"],
        ready_application.proceeding.pk,
        "null-granted",
        "New reason",
        {str(ready_application.party_id): "certificate"},
    )
    assert not PresidentialApproval.objects.filter(decision=second).exists()


def test_message_recipients_are_private_and_messages_immutable(
    ready_application, people
):
    from tribunal.services.communications import send_message, messages_for

    submit(ready_application)
    ready_application.refresh_from_db()
    app = ready_application
    other = Account.objects.create_user(
        email="spouse@example.test", email_verified=True
    )
    party = Party.objects.create(
        case=app.case, slot="B", person=other.person, account=other
    )
    send_message(people["admin"], app.case.pk, "Only A", [str(app.party_id)])
    assert len(messages_for(other, app.case.pk)) == 0
    assert len(messages_for(app.owner, app.case.pk)) == 1
    message = send_message(
        people["admin"], app.case.pk, "Both", [str(app.party_id), str(party.pk)]
    )
    assert message.recipients.count() == 2
    with pytest.raises(ValidationError):
        message.body = "Changed"
        message.save()


def test_external_link_expires_and_recipient_cannot_overwrite(
    ready_application, people
):
    from tribunal.services.reports import (
        create_request,
        send_request,
        complete_external,
    )

    submit(ready_application)
    ready_application.refresh_from_db()
    app = ready_application
    request = create_request(
        people["admin"],
        app.proceeding_id,
        app.party_id,
        "external_priest",
        "Priest report",
        [],
        "Identify the marriage",
    )
    token = send_request(people["admin"], request.pk, external_name="Fr. Test")
    report = complete_external(request.pk, token, {"testimony": "Source account"})
    assert report.revisions.get().answers["testimony"] == "Source account"
    with pytest.raises(ValidationError):
        complete_external(request.pk, token, {"testimony": "Changed"})


def test_medical_release_cannot_be_signed_for_other_person(ready_application, people):
    from tribunal.services.reports import create_request, sign_medical_release

    submit(ready_application)
    ready_application.refresh_from_db()
    app = ready_application
    request = create_request(
        people["admin"],
        app.proceeding_id,
        app.party_id,
        "medical",
        "Report",
        [],
        "Purpose",
    )
    with pytest.raises(PermissionDenied):
        sign_medical_release(
            people["admin"],
            request.pk,
            app.attachments.first().versions.first().pk,
            {"council": True},
        )


def test_closed_record_cannot_be_corrected(ready_application):
    submit(ready_application)
    ready_application.refresh_from_db()
    Proceeding.objects.filter(pk=ready_application.proceeding_id).update(
        status="closed"
    )
    Case.objects.filter(pk=ready_application.case_id).update(status="closed")
    with pytest.raises(ValidationError):
        save_answers(
            ready_application.owner, ready_application.pk, {"statement": "Changed"}, 1
        )
