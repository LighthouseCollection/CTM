"""Raw ORM queries under a real non-owner role: endpoint filters cannot make these pass."""

from contextlib import contextmanager
import pytest
from django.db import connection, transaction
from tribunal.models import (
    Account,
    Application,
    AnswerRevision,
    Attachment,
    FileVersion,
    FileTechnicalEvent,
    Notification,
    AuditEvent,
    HistoricalWorkspace,
    DocumentText,
    MedicalRelease,
    QuestionnaireVersion,
)
from tribunal.services.applications import (
    submit_application,
    start_application,
    save_answers,
)

pytestmark = pytest.mark.django_db
ROLE = "ctm_validation_runtime"


@pytest.fixture
def runtime():
    if connection.vendor != "postgresql":
        pytest.skip("PostgreSQL forced RLS test")
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1 FROM pg_roles WHERE rolname=%s", [ROLE])
        if not cursor.fetchone():
            cursor.execute(
                f"CREATE ROLE {ROLE} NOLOGIN NOSUPERUSER NOBYPASSRLS NOINHERIT"
            )
            cursor.execute(f"GRANT {ROLE} TO CURRENT_USER")
        cursor.execute(f"GRANT USAGE ON SCHEMA public TO {ROLE}")
        for signature in [
            "ctm_source_readable(text,jsonb)",
            "ctm_source_writable(text,jsonb)",
            "ctm_source_mutable(text,jsonb)",
            "ctm_source_deletable(text,jsonb)",
            "ctm_paid_filing_actor(uuid)",
            "ctm_council_visible()",
            "ctm_council_writable(text,jsonb,text)",
            "ctm_council_mutable(text,jsonb)",
        ]:
            cursor.execute(f"GRANT EXECUTE ON FUNCTION public.{signature} TO {ROLE}")
        cursor.execute(
            f"GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA public TO {ROLE}"
        )

    @contextmanager
    def enter(actor=None):
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute(f"SET LOCAL ROLE {ROLE}")
                cursor.execute(
                    "SELECT set_config('ctm.actor_id',%s,true)",
                    [str(actor.pk) if actor else ""],
                )
            try:
                yield
            finally:
                if not connection.needs_rollback:
                    with connection.cursor() as cursor:
                        cursor.execute("RESET ROLE")
                        cursor.execute("SELECT set_config('ctm.actor_id','',true)")

    return enter


def test_missing_actor_context_fails_closed(runtime, ready_application):
    with runtime():
        assert Application.objects.count() == 0
        assert AnswerRevision.objects.count() == 0
        assert FileVersion.objects.count() == 0


def test_returned_filing_projection_with_non_owner_database_role(runtime, ready_application, people):
    from tribunal.api import application_data
    from tribunal.policy import application_for
    from tribunal.services.applications import review_application

    app = ready_application
    submit_application(app.owner, app.pk, "projection-rls", {"accepted": True, "name": "John Smith"})
    review_application(people["admin"], app.pk, "reject", "Correct the date.")
    with runtime(app.owner):
        data = application_data(application_for(app.owner, app.pk), app.owner)
        assert data["can_resubmit"] and not data["can_checkout"]
        assert data["return_instructions"] == "Correct the date."
        assert data["questionnaire"]["id"] == str(app.questionnaire_id)
    other = Account.objects.create_user(email="projection-other@example.test", email_verified=True)
    with runtime(other):
        assert not Application.objects.filter(pk=app.pk).exists()


def test_applicant_raw_queries_only_return_own_sources(runtime, ready_application):
    app = ready_application
    other = Account.objects.create_user(email="other@example.test", email_verified=True)
    second = start_application(other)
    save_answers(other, second.pk, {"secret": "Other applicant"}, 0)
    with runtime(app.owner):
        assert list(Application.objects.values_list("id", flat=True)) == [app.pk]
        assert not AnswerRevision.objects.filter(application=second).exists()
    with runtime(other):
        assert not Application.objects.filter(pk=app.pk).exists()
        assert not FileVersion.objects.exists()


def test_council_raw_queries_exclude_all_unsubmitted_drafts(
    runtime, ready_application, people
):
    app = ready_application
    with runtime(people["admin"]):
        assert Application.objects.count() == 0
        assert FileVersion.objects.count() == 0
    submit_application(
        app.owner, app.pk, "rls-submitted", {"accepted": True, "name": "John Smith"}
    )
    with runtime(people["member"]):
        assert Application.objects.filter(pk=app.pk).exists()
        assert AnswerRevision.objects.filter(application=app).exists()


def test_applicant_cannot_read_old_file_versions_at_database_level(
    runtime, ready_application
):
    first = ready_application.attachments.first().versions.first()
    newer = FileVersion.objects.create(
        attachment=first.attachment,
        number=2,
        object_key="latest",
        mime_type=first.mime_type,
        byte_count=5,
        sha256="b" * 64,
        actor=ready_application.owner,
    )
    with runtime(ready_application.owner):
        assert not FileVersion.objects.filter(pk=first.pk).exists()
        assert FileVersion.objects.filter(pk=newer.pk).exists()


def test_notifications_and_system_audit_remain_private(runtime, people):
    Notification.objects.create(
        recipient=people["admin"], key="admin-only", kind="private"
    )
    AuditEvent.objects.create(actor=people["admin"], action="system", source="test")
    with runtime(people["member"]):
        assert Notification.objects.count() == 0
        assert AuditEvent.objects.count() == 0
    with runtime(people["admin"]):
        assert Notification.objects.count() == 1
        assert AuditEvent.objects.count() == 1


def test_historical_workspaces_are_publisher_private(runtime, people):
    record = HistoricalWorkspace.objects.create(
        actor=people["admin"], payload={"private": True}
    )
    with runtime(people["secretary"]):
        assert not HistoricalWorkspace.objects.filter(pk=record.pk).exists()
    with runtime(people["admin"]):
        assert HistoricalWorkspace.objects.filter(pk=record.pk).exists()


def test_suspended_actor_cannot_reuse_old_context(runtime, ready_application):
    Account.objects.filter(pk=ready_application.owner_id).update(is_active=False)
    with runtime(ready_application.owner):
        assert not Application.objects.exists()


def test_runtime_http_requests_get_session_derived_context(
    runtime, client, ready_application
):
    client.force_login(
        ready_application.owner,
        backend="allauth.account.auth_backends.AuthenticationBackend",
    )
    with runtime():
        response = client.get("/api/applications/")
        assert response.status_code == 200
        assert [item["id"] for item in response.json()["items"]] == [
            str(ready_application.pk)
        ]
        assert Application.objects.count() == 0


def test_runtime_draft_upload_and_submission_work_without_owner_bypass(
    runtime, ready_application, people, django_capture_on_commit_callbacks
):
    from django.core.files.uploadedfile import SimpleUploadedFile
    from tribunal.services.files import upload

    app = ready_application
    with runtime(app.owner), django_capture_on_commit_callbacks(execute=True):
        file = upload(
            app.owner,
            SimpleUploadedFile("evidence.pdf", b"%PDF-1.7\nsource"),
            "EVD",
            app_id=app.pk,
        )
        assert FileVersion.objects.filter(pk=file.pk).exists()
        submission = submit_application(
            app.owner,
            app.pk,
            "runtime-submit",
            {"accepted": True, "name": "John Smith"},
        )
        assert submission.application_id == app.pk


def test_runtime_cannot_forge_another_answer_actor(runtime, ready_application, people):
    from django.db import DatabaseError

    with pytest.raises(DatabaseError):
        with runtime(ready_application.owner):
            AnswerRevision.objects.create(
                application=ready_application,
                number=2,
                answers={"forged": True},
                actor=people["admin"],
            )


def test_runtime_medical_scope_is_request_specific(runtime, ready_application, people):
    from tribunal.services.reports import create_request

    app = ready_application
    submit_application(
        app.owner, app.pk, "rls-medical", {"accepted": True, "name": "John Smith"}
    )
    app.refresh_from_db()
    first = create_request(
        people["admin"], app.proceeding_id, app.party_id, "medical", "First", []
    )
    second = create_request(
        people["admin"], app.proceeding_id, app.party_id, "psychological", "Second", []
    )
    signature = app.attachments.first().versions.first()
    MedicalRelease.objects.create(
        request=first,
        subject=app.owner,
        declaration=QuestionnaireVersion.objects.get(purpose="medical_release"),
        signature=signature,
        scope={"council": True},
    )
    attachment = Attachment.objects.create(
        case=app.case,
        proceeding=app.proceeding,
        owner=app.owner,
        category="MED",
        visibility="medical",
        report_request=second,
    )
    file = FileVersion.objects.create(
        attachment=attachment,
        number=1,
        object_key="restricted-medical",
        mime_type="application/pdf",
        byte_count=1,
        sha256="c" * 64,
    )
    derivative = DocumentText.objects.create(
        file=file, engine="test", text="Restricted medical text"
    )
    with runtime(people["member"]):
        assert not FileVersion.objects.filter(pk=file.pk).exists()
        assert not DocumentText.objects.filter(pk=derivative.pk).exists()
    with runtime(app.owner):
        assert FileVersion.objects.filter(pk=file.pk).exists()


def test_runtime_staff_report_narrative_is_not_applicant_response(
    runtime, ready_application, people
):
    from tribunal.services.reports import create_request, send_request, complete_request
    from tribunal.models import ReportRevision

    app = ready_application
    submit_application(
        app.owner, app.pk, "rls-report", {"accepted": True, "name": "John Smith"}
    )
    app.refresh_from_db()
    request = create_request(
        people["admin"], app.proceeding_id, app.party_id, "intake", "Internal", []
    )
    send_request(people["admin"], request.pk)
    report = complete_request(
        people["admin"], request.pk, {"private": "Staff narrative"}
    )
    with runtime(app.owner):
        assert not ReportRevision.objects.filter(report=report).exists()
    with runtime(people["member"]):
        assert ReportRevision.objects.filter(report=report).exists()


def test_runtime_message_recipient_isolation(runtime, ready_application, people):
    from tribunal.models import Party, Message, MessageRecipient
    from tribunal.services.communications import send_message

    app = ready_application
    submit_application(
        app.owner, app.pk, "rls-message", {"accepted": True, "name": "John Smith"}
    )
    app.refresh_from_db()
    other = Account.objects.create_user(
        email="message-other@example.test", email_verified=True
    )
    Party.objects.create(
        case=app.case, account=other, person=other.person, slot="B", name="Other"
    )
    message = send_message(
        people["admin"], app.case_id, "Private to first", [app.party_id]
    )
    with runtime(other):
        assert not Message.objects.filter(pk=message.pk).exists()
        assert not MessageRecipient.objects.filter(message=message).exists()
    with runtime(app.owner):
        assert Message.objects.filter(pk=message.pk).exists()


def test_assigned_manager_can_upload_corrected_applicant_file(
    runtime, ready_application, people, django_capture_on_commit_callbacks
):
    from tribunal.services.council import assign_case
    from tribunal.services.files import upload
    from django.core.files.uploadedfile import SimpleUploadedFile

    app = ready_application
    submit_application(
        app.owner, app.pk, "rls-staff-file", {"accepted": True, "name": "John Smith"}
    )
    app.refresh_from_db()
    assign_case(
        people["admin"], app.case_id, people["member"].pk, people["president"].pk
    )
    old = app.attachments.get(category="MC")
    with runtime(people["member"]), django_capture_on_commit_callbacks(execute=True):
        file = upload(
            people["member"],
            SimpleUploadedFile("corrected.pdf", b"%PDF-1.7\ncorrection"),
            "MC",
            app_id=app.pk,
            attachment_id=old.pk,
        )
        assert file.actor_id == people["member"].pk
        assert file.attachment.owner_id == app.owner_id


def test_unassigned_member_cannot_take_ownership_of_a_readable_filing(
    runtime, ready_application, people
):
    app = ready_application
    submit_application(
        app.owner, app.pk, "rls-takeover", {"accepted": True, "name": "John Smith"}
    )
    with runtime(people["member"]):
        changed = Application.objects.filter(pk=app.pk).update(
            owner=people["member"], case=None, proceeding=None, party=None
        )
        assert changed == 0
    app.refresh_from_db()
    assert app.owner_id == people["applicant"].pk


def test_submitted_history_cannot_be_changed_back_to_disposable_draft(
    runtime, ready_application
):
    from django.db import DatabaseError

    app = ready_application
    submit_application(
        app.owner, app.pk, "rls-retain", {"accepted": True, "name": "John Smith"}
    )
    with pytest.raises(DatabaseError):
        with runtime(app.owner):
            Application.objects.filter(pk=app.pk).update(
                status="draft", submitted_at=None
            )
    app.refresh_from_db()
    assert app.submitted_at is not None
    assert app.submissions.count() == 1


def test_draft_owner_can_delete_ocr_derivatives_with_private_draft(
    runtime, ready_application
):
    from tribunal.services.retention import remove_draft

    file = ready_application.attachments.first().versions.first()
    derivative = DocumentText.objects.create(
        file=file, engine="test", text="Private draft OCR"
    )
    with runtime(ready_application.owner):
        remove_draft(ready_application.owner, ready_application.pk)
    assert not DocumentText.objects.filter(pk=derivative.pk).exists()


def test_released_certificate_does_not_expose_an_unreleased_later_version(
    runtime, ready_application, people
):
    from tribunal.services.decisions import (
        record_decision,
        approve_decision,
        attest_signature,
        issue_decree,
        release_decree,
    )

    app = ready_application
    submit_application(
        app.owner, app.pk, "rls-decree", {"accepted": True, "name": "John Smith"}
    )
    app.refresh_from_db()
    decision = record_decision(
        people["admin"],
        app.proceeding_id,
        "diss-applicant",
        "Reason",
        {str(app.party_id): "certificate"},
    )
    approve_decision(people["president"], decision.pk)
    attachment = Attachment.objects.create(
        case=app.case, proceeding=app.proceeding, category="DCR", visibility="council"
    )
    file = FileVersion.objects.create(
        attachment=attachment,
        number=1,
        object_key="signed-rls.pdf",
        mime_type="application/pdf",
        byte_count=1,
        sha256="d" * 64,
    )
    FileTechnicalEvent.objects.create(file=file, task="scan", result="clean")
    attest_signature(
        people["admin"],
        file.pk,
        people["president"].pk,
        "signed_scan",
        {"confirmed_signed": True},
    )
    decree = issue_decree(people["admin"], decision.pk, file.pk, people["president"].pk)
    release_decree(people["admin"], decree.pk, app.party_id)
    later = FileVersion.objects.create(
        attachment=attachment,
        number=2,
        object_key="unreleased-rls.pdf",
        mime_type="application/pdf",
        byte_count=1,
        sha256="e" * 64,
    )
    text = DocumentText.objects.create(
        file=later, engine="test", text="Unreleased certificate"
    )
    with runtime(app.owner):
        assert FileVersion.objects.filter(pk=file.pk).exists()
        assert not FileVersion.objects.filter(pk=later.pk).exists()
        assert not DocumentText.objects.filter(pk=text.pk).exists()


def test_external_priest_submission_uses_capability_not_a_council_actor(
    runtime, client, ready_application, people
):
    from tribunal.services.reports import create_request, send_request
    from tribunal.services.council import assign_case
    from tribunal.models import Report, ReportRevision

    app = ready_application
    submit_application(
        app.owner, app.pk, "rls-external", {"accepted": True, "name": "John Smith"}
    )
    app.refresh_from_db()
    assign_case(
        people["admin"], app.case_id, people["member"].pk, people["president"].pk
    )
    request = create_request(
        people["admin"],
        app.proceeding_id,
        app.party_id,
        "external_priest",
        "Priest report",
        [],
    )
    token = send_request(people["admin"], request.pk, external_name="Fr. Test")
    with runtime():
        response = client.post(
            f"/external/reports/{request.pk}/",
            data='{"answers":{"testimony":"Priest account"}}',
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        assert response.status_code == 201
        assert ReportRevision.objects.count() == 0
    report = Report.objects.get(request=request)
    assert report.revisions.get().actor_id is None
    assert (
        Notification.objects.filter(
            recipient=people["member"], kind="report_received"
        ).count()
        == 1
    )
    with runtime(people["member"]):
        assert ReportRevision.objects.filter(report=report).exists()


def test_notification_retry_does_not_require_reading_another_recipients_inbox(
    runtime, ready_application, people
):
    from tribunal.services.common import notify

    with runtime(ready_application.owner):
        notify(people["admin"], "test_update", ready_application)
        notify(people["admin"], "test_update", ready_application)
        assert not Notification.objects.filter(recipient=people["admin"]).exists()
    assert (
        Notification.objects.filter(
            recipient=people["admin"], kind="test_update"
        ).count()
        == 1
    )


def test_verified_payment_and_paid_filing_recovery_work_without_an_interactive_session(
    runtime, ready_application
):
    from tribunal.models import FeeObligation
    from tribunal.services.payments import (
        prepare_checkout,
        process_paid_checkout,
        finalize_paid_intent,
    )

    app = ready_application
    FeeObligation.objects.filter(application=app).update(status="due", waived_by=None)
    with runtime(app.owner):
        intent = prepare_checkout(
            app.owner, app.pk, {"accepted": True, "name": "John Smith"}
        )
    with runtime():
        paid = process_paid_checkout(
            "evt_non_owner",
            {
                "id": "cs_non_owner",
                "client_reference_id": str(intent.pk),
                "metadata": {"ctm_intent": str(intent.pk)},
                "amount_total": 25000,
                "currency": "usd",
                "payment_status": "paid",
            },
        )
        submission = finalize_paid_intent(paid.pk)
        assert submission.application_id == app.pk
        assert Application.objects.count() == 0


def test_security_definer_helpers_are_not_executable_by_public(runtime):
    with connection.cursor() as cursor:
        cursor.execute("""SELECT p.proname FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace,
           LATERAL aclexplode(coalesce(p.proacl,acldefault('f',p.proowner))) access
           WHERE n.nspname='public' AND p.proname LIKE 'ctm_%%' AND p.prosecdef AND access.grantee=0 AND access.privilege_type='EXECUTE'""")
        assert cursor.fetchall() == []


@pytest.mark.parametrize("signed_in", [False, True])
def test_signed_payment_webhook_is_validated_under_non_owner_role(
    runtime, client, ready_application, signed_in
):
    import json, hmac, hashlib, time
    from django.test import override_settings
    from tribunal.models import FeeObligation
    from tribunal.services.payments import prepare_checkout

    app = ready_application
    if signed_in:
        other = Account.objects.create_user(
            email="webhook-browser@example.test", email_verified=True
        )
        client.force_login(
            other, backend="allauth.account.auth_backends.AuthenticationBackend"
        )
    FeeObligation.objects.filter(application=app).update(status="due", waived_by=None)
    with runtime(app.owner):
        intent = prepare_checkout(
            app.owner, app.pk, {"accepted": True, "name": "John Smith"}
        )
    payload = json.dumps(
        {
            "id": "evt_signed_rls",
            "object": "event",
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_signed_rls",
                    "payment_status": "paid",
                    "amount_total": 25000,
                    "currency": "usd",
                    "client_reference_id": str(intent.pk),
                    "metadata": {"ctm_intent": str(intent.pk)},
                }
            },
        }
    )
    secret = "whsec_isolated_test_only"
    timestamp = str(int(time.time()))
    signature = hmac.new(
        secret.encode(), f"{timestamp}.{payload}".encode(), hashlib.sha256
    ).hexdigest()
    with override_settings(STRIPE_WEBHOOK_SECRET=secret), runtime():
        invalid = client.post(
            "/integrations/stripe/",
            data=payload,
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE=f"t={timestamp},v1=bad",
        )
        assert invalid.status_code == 400
        valid = client.post(
            "/integrations/stripe/",
            data=payload,
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE=f"t={timestamp},v1={signature}",
        )
        assert valid.status_code == 200
        assert valid.json() == {"received": True}
    app.refresh_from_db()
    assert app.status == "submitted" and app.submissions.count() == 1


@pytest.mark.django_db(transaction=True)
def test_rls_migration_can_be_reversed_and_reapplied():
    if connection.vendor != "postgresql":
        pytest.skip("PostgreSQL migration round trip")
    from django.db.migrations.executor import MigrationExecutor

    try:
        MigrationExecutor(connection).migrate(
            [("tribunal", "0010_alter_recording_file_and_more")]
        )
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT count(*) FROM pg_class WHERE relname='tribunal_application' AND relforcerowsecurity"
            )
            assert cursor.fetchone()[0] == 0
    finally:
        MigrationExecutor(connection).migrate([("tribunal", "0012_council_privacy")])
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT count(*) FROM pg_class WHERE relname='tribunal_application' AND relrowsecurity AND relforcerowsecurity"
        )
        assert cursor.fetchone()[0] == 1


@pytest.fixture
def council_sources(ready_application, people):
    from datetime import date
    from tribunal.services import council
    from tribunal import models as m

    app = ready_application
    submit_application(
        app.owner, app.pk, "council-privacy", {"accepted": True, "name": "John Smith"}
    )
    app.refresh_from_db()
    council.assign_case(
        people["admin"], app.case_id, people["member"].pk, people["president"].pk
    )
    session = council.create_session(people["admin"], date(2026, 11, 9))
    item = council.place_agenda(people["member"], session.pk, app.case_id)
    council.record_attendance(people["admin"], session.pk, people["member"].pk, True)
    hearing = council.hear_case(people["member"], item.pk)
    council.save_hearing_outcome(
        people["member"], hearing.pk, "Internal outcome", "Gather information"
    )
    note = council.save_note(people["member"], app.proceeding_id, "Private note")
    council.save_finding(
        people["member"], app.proceeding_id, "sample", {"text": "Private finding"}
    )
    models = [
        m.CouncilSession,
        m.AgendaItem,
        m.Attendance,
        m.Hearing,
        m.HearingOutcome,
        m.CaseAssignment,
        m.CaseNote,
        m.NoteRevision,
        m.FindingRevision,
    ]
    return app, session, hearing, note, models


@pytest.mark.parametrize("role", [None, "applicant"])
def test_council_sources_are_hidden_from_non_council_raw_queries(
    runtime, council_sources, people, role
):
    *_, models = council_sources
    with runtime(people[role] if role else None):
        assert {model.__name__: model.objects.count() for model in models} == {
            model.__name__: 0 for model in models
        }


def test_all_authorized_council_can_read_internal_sources(
    runtime, council_sources, people
):
    *_, models = council_sources
    with runtime(people["president"]):
        assert all(model.objects.exists() for model in models)


def test_raw_session_attendance_insert_cannot_impersonate_secretary(
    runtime, council_sources, people
):
    from django.db import DatabaseError
    from tribunal.models import Attendance

    _, session, _, _, _ = council_sources
    with pytest.raises(DatabaseError):
        with runtime(people["member"]):
            Attendance.objects.create(
                session=session,
                member=people["president"],
                present=True,
                actor=people["secretary"],
            )


def test_internal_note_owner_cannot_be_taken_over(runtime, council_sources, people):
    from tribunal.models import CaseNote

    _, _, _, note, _ = council_sources
    with runtime(people["president"]):
        assert (
            CaseNote.objects.filter(pk=note.pk).update(author=people["president"]) == 0
        )
    note.refresh_from_db()
    assert note.author_id == people["member"].pk


def test_unassigned_member_cannot_insert_findings_using_raw_orm(
    runtime, council_sources, people
):
    from django.db import DatabaseError
    from tribunal.models import FindingRevision

    app, *_ = council_sources
    with pytest.raises(DatabaseError):
        with runtime(people["president"]):
            FindingRevision.objects.create(
                proceeding=app.proceeding,
                fact_code="forged",
                number=1,
                value={},
                actor=people["president"],
            )


def test_legitimate_council_workflow_writes_under_non_owner_role(
    runtime, council_sources, people
):
    from datetime import date
    from tribunal.services import council

    app, *_ = council_sources
    with runtime(people["admin"]):
        session = council.create_session(people["admin"], date(2026, 11, 12))
        council.record_attendance(
            people["admin"], session.pk, people["member"].pk, True
        )
    with runtime(people["member"]):
        item = council.place_agenda(people["member"], session.pk, app.case_id)
        hearing = council.hear_case(people["member"], item.pk)
        note = council.save_note(people["member"], app.proceeding_id, "Runtime note")
        assert note.author_id == people["member"].pk
        council.save_finding(
            people["member"], app.proceeding_id, "runtime", {"value": True}
        )
        council.save_hearing_outcome(
            people["member"], hearing.pk, "Private runtime outcome", "Follow up"
        )
    with runtime(people["admin"]):
        council.close_session(people["admin"], session.pk)
    with runtime(people["member"]):
        council.save_hearing_outcome(
            people["member"],
            hearing.pk,
            "Corrected after session close",
            "Revised follow up",
        )


def test_session_date_cannot_be_changed_in_place_by_runtime_admin(
    runtime, council_sources, people
):
    from datetime import timedelta
    from django.db import DatabaseError
    from tribunal.models import CouncilSession

    _, session, *_ = council_sources
    with pytest.raises(DatabaseError):
        with runtime(people["admin"]):
            CouncilSession.objects.filter(pk=session.pk).update(
                date=session.date + timedelta(days=1)
            )


def test_council_record_deletion_is_denied_to_runtime_admin(
    runtime, council_sources, people
):
    _, session, *_ = council_sources
    with runtime(people["admin"]):
        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM public.tribunal_councilsession WHERE id=%s",
                [str(session.pk)],
            )
            assert cursor.rowcount == 0


def test_new_assignee_cannot_append_to_previous_authors_note(
    runtime, council_sources, people
):
    from django.db import DatabaseError
    from tribunal.models import NoteRevision
    from tribunal.services.council import assign_case

    app, _, _, note, _ = council_sources
    assign_case(
        people["admin"], app.case_id, people["president"].pk, people["president"].pk
    )
    with pytest.raises(DatabaseError):
        with runtime(people["president"]):
            NoteRevision.objects.create(
                note=note, number=2, text="Forged revision", actor=people["president"]
            )


def test_assigned_presenter_cannot_record_attendance_revisions_directly(
    runtime, council_sources, people
):
    from django.db import DatabaseError
    from tribunal.models import Attendance

    _, session, hearing, _, _ = council_sources
    with pytest.raises(DatabaseError):
        with runtime(people["member"]):
            Attendance.objects.create(
                session=session,
                hearing=hearing,
                member=people["president"],
                present=True,
                actor=people["member"],
            )


def test_closed_council_session_cannot_be_reopened_by_raw_update(
    runtime, council_sources, people
):
    from django.db import DatabaseError
    from tribunal.services.council import close_session
    from tribunal.models import CouncilSession

    _, session, *_ = council_sources
    with runtime(people["admin"]):
        close_session(people["admin"], session.pk)
        assert close_session(people["admin"], session.pk).state == "closed"
    with pytest.raises(DatabaseError):
        with runtime(people["admin"]):
            CouncilSession.objects.filter(pk=session.pk).update(state="planned")
