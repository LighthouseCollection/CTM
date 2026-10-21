import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.utils import timezone
from tribunal.models import (
    Account,
    Party,
    OpenCaseClaim,
    Case,
    Proceeding,
    Application,
    FeeObligation,
    FileVersion,
    FileTechnicalEvent,
    Attachment,
    Notification,
)
from tribunal.services.applications import (
    start_application,
    save_answers,
    submit_application,
    waive_fee,
)
from tribunal.services.decisions import (
    withdraw_application,
    decide_appeal,
    add_appeal_information,
)
from tribunal.services.council import (
    assign_case,
    create_session,
    place_agenda,
    hear_case,
    close_session,
)

pytestmark = pytest.mark.django_db


def initial(app):
    submit_application(
        app.owner, app.pk, "initial", {"accepted": True, "name": "John Smith"}
    )
    app.refresh_from_db()
    return app


def test_sole_withdrawal_closes_without_other_party_notice(ready_application, people):
    app = initial(ready_application)
    other = Account.objects.create_user(email="other@example.test", email_verified=True)
    Party.objects.create(
        case=app.case, slot="B", person=other.person, account=other, participating=False
    )
    withdraw_application(app.owner, app.pk)
    app.case.refresh_from_db()
    assert app.case.status == "closed"
    assert not Notification.objects.filter(recipient=other).exists()
    assert not OpenCaseClaim.objects.filter(person=app.owner.person).exists()


def test_accepted_appeal_reopens_same_case_and_locks_original(
    ready_application, people
):
    app = initial(ready_application)
    assign_case(
        people["admin"], app.case_id, people["member"].pk, people["president"].pk
    )
    withdraw_application(app.owner, app.pk)
    appeal = start_application(app.owner, app.case_id, "appeal")
    save_answers(
        app.owner,
        appeal.pk,
        {"statement": "Disagree", "new_information": "New evidence"},
        0,
    )
    waive_fee(people["admin"], appeal.pk)
    submit_application(
        app.owner, appeal.pk, "appeal", {"accepted": True, "name": "John Smith"}
    )
    supplement = add_appeal_information(app.owner, appeal.pk, "Extra information")
    assert supplement.text == "Extra information"
    session = create_session(people["admin"], timezone.localdate())
    agenda = place_agenda(people["admin"], session.pk, app.case_id)
    hearing = hear_case(people["member"], agenda.pk)
    result = decide_appeal(people["member"], appeal.pk, hearing.pk, "accept")
    app.case.refresh_from_db()
    app.proceeding.refresh_from_db()
    assert app.case.status == "open"
    assert result.reopened_proceeding.case_id == app.case_id
    assert result.reopened_proceeding.sequence == 1
    assert app.proceeding.status == "closed"


def test_time_exhausted_carries_but_deliberate_deferral_does_not(
    ready_application, people
):
    app = initial(ready_application)
    first = create_session(people["admin"], timezone.localdate())
    second = create_session(
        people["admin"], timezone.localdate() + timezone.timedelta(days=7)
    )
    item = place_agenda(people["admin"], first.pk, app.case_id)
    close_session(people["admin"], first.pk)
    assert second.agenda.get().carried_from_id == item.pk


def test_current_file_only_and_closed_upload_rejected(ready_application):
    from tribunal.services.files import authorized_file, upload
    from django.core.files.uploadedfile import SimpleUploadedFile

    app = initial(ready_application)
    attachment = app.attachments.first()
    old = attachment.versions.get()
    newer = FileVersion.objects.create(
        attachment=attachment,
        number=2,
        object_key="test/new",
        original_name="new.pdf",
        display_name="new.pdf",
        mime_type="application/pdf",
        byte_count=5,
        sha256="b" * 64,
        actor=app.owner,
    )
    FileTechnicalEvent.objects.create(file=newer, task="scan", result="clean")
    with pytest.raises(PermissionDenied):
        authorized_file(app.owner, old.pk)
    assert authorized_file(app.owner, newer.pk).pk == newer.pk
    withdraw_application(app.owner, app.pk)
    with pytest.raises(ValidationError):
        upload(
            app.owner,
            SimpleUploadedFile("x.pdf", b"%PDF-x"),
            attachment.category,
            app.pk,
        )


def test_cross_case_message_link_denied(ready_application, people):
    from tribunal.services.communications import send_message

    app = initial(ready_application)
    other_case = Case.objects.create(number="historic-1")
    other_attachment = Attachment.objects.create(case=other_case, category="MC")
    file = FileVersion.objects.create(
        attachment=other_attachment,
        number=1,
        object_key="other",
        original_name="x.pdf",
        display_name="x.pdf",
        mime_type="application/pdf",
        byte_count=1,
        sha256="c" * 64,
    )
    with pytest.raises(ValidationError):
        send_message(
            people["admin"],
            app.case_id,
            "Private",
            [str(app.party_id)],
            file_ids=[str(file.pk)],
        )


def test_signature_and_current_approval_required_for_decree(ready_application, people):
    from tribunal.services.decisions import record_decision, issue_decree

    app = initial(ready_application)
    decision = record_decision(
        people["admin"],
        app.proceeding_id,
        "diss-applicant",
        "Reason",
        {str(app.party_id): "certificate"},
    )
    with pytest.raises(ValidationError):
        issue_decree(
            people["admin"],
            decision.pk,
            app.attachments.first().versions.first().pk,
            people["president"].pk,
        )
