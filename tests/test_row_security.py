"""Raw ORM queries under a real non-owner role: endpoint filters cannot make these pass."""

from contextlib import contextmanager
import pytest
from django.db import connection, transaction
from django.core.exceptions import ValidationError
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
            "ctm_decision_readable(text,jsonb)",
            "ctm_decision_writable(text,jsonb)",
            "ctm_decree_writable(jsonb)",
            "ctm_finance_readable(text,jsonb)",
            "ctm_review_readable(jsonb)",
            "ctm_finance_writable(text,jsonb)",
            "ctm_finance_notice(text,jsonb)",
            "ctm_fee_can_waive(uuid)",
            "ctm_session_transfer_context(uuid)",
            "ctm_testimony_readable(text,jsonb)",
            "ctm_testimony_writable(text,jsonb)",
            "ctm_invitation_context(uuid)",
            "ctm_returned_source_visible(text,jsonb)",
            "ctm_library_readable(text,jsonb)",
            "ctm_library_writable(text,jsonb)",
            "ctm_assessment_release_metadata(uuid)",
            "ctm_reference_readable(text,jsonb)",
            "ctm_reference_writable(text,jsonb)",
            "ctm_staff_readable()",
            "ctm_staff_writable(text,jsonb)",
            "ctm_staff_mutable(text,jsonb)",
            "ctm_council_result_update(jsonb)",
            "ctm_reconsideration_readable(jsonb)",
            "ctm_reconsideration_writable(text,jsonb)",
            "ctm_request_readable(jsonb)",
            "ctm_request_writable(jsonb,text)",
            "ctm_report_root_readable(jsonb)",
            "ctm_report_root_writable(jsonb)",
            "ctm_request_source_writable(text,jsonb)",
            "ctm_call_readable()",
            "ctm_call_writable(jsonb)",
            "ctm_media_readable(text,jsonb)",
            "ctm_media_writable(text,jsonb,text)",
            "ctm_pending_readable(jsonb)",
            "ctm_pending_writable(jsonb,text)",
            "ctm_media_status(uuid)",
            "ctm_supplement_manifest_valid(jsonb)",
            "ctm_allocate_case_number(date)",
            "ctm_message_delivery_valid(uuid,uuid)",
            "ctm_draft_warning_current(uuid,timestamptz,uuid)",
            "ctm_orphan_cleanup_allowed(text)",
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


def test_notification_source_and_first_read_cannot_be_rewritten(runtime, people):
    from django.utils import timezone
    from django.db import DatabaseError
    row = Notification.objects.create(recipient=people["applicant"], key="retained-notification",
                                      kind="report_requested", payload={"synthetic": True})
    for change in [{"recipient": people["member"]}, {"payload": {}}, {"key": "rebound"}, {"kind": "different"}]:
        with pytest.raises(DatabaseError):
            with runtime(people["applicant"]):
                Notification.objects.filter(pk=row.pk).update(**change)
    with runtime(people["member"]):
        assert Notification.objects.filter(pk=row.pk).update(read_at=timezone.now()) == 0
    with runtime(people["applicant"]):
        assert Notification.objects.filter(pk=row.pk).update(read_at=timezone.now()) == 1
    row.refresh_from_db()
    first = row.read_at
    with pytest.raises(DatabaseError):
        with runtime(people["applicant"]):
            Notification.objects.filter(pk=row.pk).update(read_at=None)
    with pytest.raises(DatabaseError):
        with transaction.atomic():
            Notification.objects.filter(pk=row.pk).delete()
    row.refresh_from_db()
    assert row.read_at == first and row.payload == {"synthetic": True}


def test_report_version_gate_and_closed_receipt_recovery_under_rls(runtime, ready_application, people):
    from tribunal.models import Proceeding
    from tribunal.services.reports import create_request, send_request, complete_request, revise_report
    from tribunal.validation import VersionConflict
    submit_application(ready_application.owner, ready_application.pk, "rls-report-revision", {"accepted": True, "name": "John Smith"})
    ready_application.refresh_from_db()
    with runtime(people["admin"]):
        request = create_request(people["admin"], ready_application.proceeding_id, ready_application.party_id, "interview", "Synthetic interview", [])
        send_request(people["admin"], request.pk)
        report = complete_request(people["admin"], request.pk, {"answer": "Original"})
        revision = revise_report(people["admin"], report.pk, {"answer": "Corrected"}, expected_version=1)
        with pytest.raises(VersionConflict):
            revise_report(people["admin"], report.pk, {"answer": "Stale"}, expected_version=1)
    Proceeding.objects.filter(pk=ready_application.proceeding_id).update(status="closed")
    with runtime(people["admin"]):
        assert revise_report(people["admin"], report.pk, revision.answers, expected_version=1).pk == revision.pk
        with pytest.raises(ValidationError):
            revise_report(people["admin"], report.pk, {"answer": "New"}, expected_version=2)


def test_council_compare_save_vote_replay_and_unique_versions_under_rls(runtime, ready_application, people):
    from tribunal import models as m
    from tribunal.services.council import save_note, save_finding
    from tribunal.services.decisions import record_decision, cast_vote
    from tribunal.validation import VersionConflict
    from django.db import IntegrityError
    submit_application(ready_application.owner, ready_application.pk, "runtime-council-versions", {"accepted": True, "name": "John Smith"})
    ready_application.refresh_from_db()
    with runtime(people["admin"]):
        note = save_note(people["admin"], ready_application.proceeding_id, "Original", expected_version=0)
        save_note(people["admin"], ready_application.proceeding_id, "Changed", note.pk, expected_version=1)
        finding = save_finding(people["admin"], ready_application.proceeding_id, "fact", {"source": "Note"}, [{"note_id": str(note.pk)}], expected_version=0)
        decision = record_decision(people["admin"], ready_application.proceeding_id, "deferred", "Reason", {}, expected_version=0)
        vote = cast_vote(people["admin"], decision.pk, "approve", idempotency_key="runtime-vote")
        assert cast_vote(people["admin"], decision.pk, "approve", idempotency_key="runtime-vote").pk == vote.pk
        with pytest.raises(VersionConflict):
            save_finding(people["admin"], ready_application.proceeding_id, "fact", {"changed": True}, expected_version=0)
    for model, values in [(m.NoteRevision, {"note": note, "number": 1, "text": "Duplicate"}),
                          (m.FindingRevision, {"proceeding_id": ready_application.proceeding_id, "fact_code": "fact", "number": 1, "value": {}})]:
        with pytest.raises(IntegrityError):
            with runtime(people["admin"]):
                model.objects.create(actor=people["admin"], **values)


def test_historical_workspace_monotonic_versions_under_rls(runtime, people):
    from tribunal.services.historical import stage, publish
    from django.db import DatabaseError
    with runtime(people["admin"]):
        workspace = stage(people["admin"], {"number": "RUNTIME-LEGACY", "status": "closed"})
        workspace = stage(people["admin"], {"number": "RUNTIME-LEGACY", "status": "closed", "parties": []}, workspace.pk, expected_version=1)
        assert workspace.version == 2
    with pytest.raises(DatabaseError):
        with runtime(people["admin"]):
            HistoricalWorkspace.objects.filter(pk=workspace.pk).update(payload={})
    with runtime(people["admin"]):
        case = publish(people["admin"], workspace.pk, expected_version=2)
        assert case.origin == "historical"
    with runtime(people["secretary"]):
        assert not HistoricalWorkspace.objects.filter(pk=workspace.pk).exists()


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
    runtime, unpaid_application
):
    from tribunal.models import FeeObligation
    from tribunal.services.payments import (
        prepare_checkout,
        process_paid_checkout,
        finalize_paid_intent,
    )

    app = unpaid_application
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
    runtime, client, unpaid_application, signed_in
):
    import json, hmac, hashlib, time
    from django.test import override_settings
    from tribunal.models import FeeObligation
    from tribunal.services.payments import prepare_checkout

    app = unpaid_application
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
        MigrationExecutor(connection).migrate([("tribunal", "0035_queue_source_and_cleanup_guards")])
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT count(*) FROM pg_class WHERE relname='tribunal_application' AND relrowsecurity AND relforcerowsecurity"
        )
        assert cursor.fetchone()[0] == 1


def test_pending_application_files_under_runtime_role(runtime, ready_application):
    from tribunal.services.files import application_file_listing

    app = ready_application
    file = app.attachments.get(category="MC").versions.first()
    FileTechnicalEvent.objects.create(file=file, task="scan", result="pending")
    with runtime(app.owner):
        data = application_file_listing(app.owner, app.pk)
        row = next(x for x in data["items"] if x["category"] == "MC")
        assert row["scan_state"] == "pending" and "download_url" not in row
        assert data["can_upload"]


def test_decision_policies_allow_self_vote_and_block_forgery(runtime, ready_application, people):
    from django.db import DatabaseError
    from tribunal.models import DecisionRevision, Vote, PresidentialApproval
    from tribunal.services.decisions import record_decision, cast_vote, approve_decision
    from tribunal.services.council import assign_case

    app = ready_application
    submit_application(app.owner, app.pk, "decision-rls", {"accepted": True, "name": "John Smith"})
    app.refresh_from_db()
    assign_case(people["admin"], app.case_id, people["member"].pk, people["president"].pk)
    with runtime(people["member"]):
        first = record_decision(people["member"], app.proceeding_id, "diss-both", "Grounds", {})
        cast_vote(people["member"], first.pk, "approve")
    with runtime(people["president"]):
        cast_vote(people["president"], first.pk, "abstain")
        approve_decision(people["president"], first.pk)
    with runtime(app.owner):
        assert not DecisionRevision.objects.exists() and not Vote.objects.exists()
        assert not PresidentialApproval.objects.exists()
    with pytest.raises(DatabaseError), runtime(people["member"]):
        Vote.objects.create(decision=first, member=people["president"], actor=people["member"], choice="approve")
    with pytest.raises(DatabaseError), runtime(people["member"]):
        PresidentialApproval.objects.create(decision=first, president=people["president"], actor=people["member"])
    with runtime(people["admin"]):
        second = record_decision(people["admin"], app.proceeding_id, "deferred", "New inquiry", {})
        assert second.number == 2
    with pytest.raises(DatabaseError), runtime(people["member"]):
        Vote.objects.create(decision=first, member=people["member"], actor=people["member"], choice="deny")
    with runtime():
        assert not DecisionRevision.objects.exists()


def test_decree_policies_require_signature_and_exact_release(runtime, ready_application, people):
    from django.db import DatabaseError
    from django.utils import timezone
    from tribunal.models import Decree, DecreeRelease
    from tribunal.services.decisions import record_decision, approve_decision, attest_signature, issue_decree, release_decree

    app = ready_application
    submit_application(app.owner, app.pk, "decree-rls", {"accepted": True, "name": "John Smith"})
    app.refresh_from_db()
    decision = record_decision(people["admin"], app.proceeding_id, "diss-applicant", "Grounds", {str(app.party_id): "certificate"})
    approve_decision(people["president"], decision.pk)
    attachment = Attachment.objects.create(case=app.case, proceeding=app.proceeding, category="DEC", visibility="council")
    file = FileVersion.objects.create(attachment=attachment, number=1, object_key="rls/signed.pdf",
        original_name="signed.pdf", display_name="signed.pdf", mime_type="application/pdf",
        byte_count=5, sha256="d"*64, actor=people["admin"])
    FileTechnicalEvent.objects.create(file=file, task="scan", result="clean")
    with pytest.raises(DatabaseError), runtime(people["admin"]):
        Decree.objects.create(decision=decision, reference="forged", language="en", signed_file=file,
            signer=people["president"], issued_at=timezone.now())
    with runtime(people["president"]):
        attest_signature(people["president"], file.pk, people["president"].pk, "signed_scan", {"confirmed_signed": True})
    with runtime(people["admin"]):
        decree = issue_decree(people["admin"], decision.pk, file.pk, people["president"].pk)
    with runtime(app.owner):
        assert not Decree.objects.exists() and not FileVersion.objects.filter(pk=file.pk).exists()

    with runtime(people["secretary"]):
        release_decree(people["secretary"], decree.pk, app.party_id)
    with runtime(app.owner):
        assert Decree.objects.get().pk == decree.pk
        assert DecreeRelease.objects.count() == 1
        assert FileVersion.objects.filter(pk=file.pk).exists()
    with runtime(people["secretary"]):
        release_decree(people["secretary"], decree.pk, app.party_id, "withdraw")
    with runtime(app.owner):
        assert not Decree.objects.exists() and not FileVersion.objects.filter(pk=file.pk).exists()


def test_finance_policies_reject_forged_payment_and_snapshot_changes(runtime, unpaid_application):
    from django.db import DatabaseError
    from tribunal.models import FeeObligation, CheckoutIntent, PaymentEvent
    from tribunal.services.payments import prepare_checkout

    app = unpaid_application
    with runtime(app.owner):
        intent = prepare_checkout(app.owner, app.pk, {"accepted": True, "name": "John Smith"})
    with pytest.raises(DatabaseError), runtime(app.owner):
        PaymentEvent.objects.create(application=app, provider_event_id="evt_forged", kind="paid",
            amount_minor=25000, currency="USD", provider_reference="cs_forged")
    with pytest.raises(DatabaseError), runtime(app.owner):
        FeeObligation.objects.filter(application=app).update(status="paid")
    with pytest.raises(DatabaseError), runtime(app.owner):
        CheckoutIntent.objects.filter(pk=intent.pk).update(attestation={"accepted": True, "name": "Changed"})
    outsider = Account.objects.create_user(email="finance-other@example.test", email_verified=True)
    with runtime(outsider):
        assert not CheckoutIntent.objects.exists() and not FeeObligation.objects.exists() and not PaymentEvent.objects.exists()


def test_non_owner_finance_events_keep_formal_submission(runtime, unpaid_application, people):
    from tribunal.models import PaymentEvent, FeeObligation
    from tribunal.services.payments import prepare_checkout, process_paid_checkout, finalize_paid_intent, process_finance_event

    app = unpaid_application
    with runtime(app.owner):
        intent = prepare_checkout(app.owner, app.pk, {"accepted": True, "name": "John Smith"})
    with runtime():
        process_paid_checkout("evt_finance_paid", {"id": "cs_finance", "metadata": {"ctm_intent": str(intent.pk)},
            "client_reference_id": str(intent.pk), "payment_status": "paid", "amount_total": 25000,
            "currency": "usd", "payment_intent": "pi_finance"})
        submission = finalize_paid_intent(intent.pk)
        event = process_finance_event("evt_finance_dispute", {"payment_intent": "pi_finance", "amount": 25000, "currency": "usd"}, "chargeback")
        assert not PaymentEvent.objects.exists()
    with runtime(app.owner):
        assert app.submissions.get().pk == submission.pk
        assert PaymentEvent.objects.filter(pk=event.pk, kind="chargeback").exists()
        assert FeeObligation.objects.get(application=app).status == "paid"
    for role in ["admin", "secretary"]:
        with runtime(people[role]):
            assert Notification.objects.filter(kind="payment_finance_review").exists()


def test_administrative_waiver_does_not_grant_draft_answer_access(runtime, unpaid_application, people):
    from tribunal.services.applications import waive_fee
    from tribunal.models import FeeObligation

    app = unpaid_application
    with runtime(people["secretary"]):
        assert not Application.objects.filter(pk=app.pk).exists()
        waived = waive_fee(people["secretary"], app.pk)
        assert waived.status == "waived"
        assert not AnswerRevision.objects.filter(application=app).exists()
    with runtime(app.owner):
        assert FeeObligation.objects.get(application=app).waived_by_id == people["secretary"].pk


def test_satisfied_fee_cannot_be_reset_or_waiver_actor_rewritten(runtime, ready_application):
    from django.db import DatabaseError
    from tribunal.models import FeeObligation

    app = ready_application
    with pytest.raises(DatabaseError), runtime(app.owner):
        FeeObligation.objects.filter(application=app).update(status="due", waived_by=None)
    with pytest.raises(DatabaseError), runtime(app.owner):
        FeeObligation.objects.filter(application=app).update(waived_by=app.owner)


def test_readiness_gate_rejects_owner_and_reports_remaining_runtime_gaps(runtime):
    from tribunal.services.readiness import database_readiness

    owner = database_readiness()
    assert not owner["ready_for_deployment"]
    assert owner["checks"]["owned_or_owner_role_accessible_tables"]
    with runtime():
        report = database_readiness()
        assert not report["ready_for_deployment"]
        assert not any(report["checks"]["role_attributes"].values())
        assert not report["checks"]["owned_or_owner_role_accessible_tables"]
        assert report["checks"]["forced_rls_table_count"] == 56
        assert "tribunal_reportrequest" not in report["checks"]["unreviewed_domain_tables"]
        assert not report["checks"]["public_security_definer_helpers"]


def test_cleanup_reference_check_sees_files_hidden_from_runtime_actor(runtime, ready_application, people, settings, tmp_path):
    from tribunal.services.queue import enqueue_cleanup, cleanup_orphan
    from tribunal.services.files import private_path, write_private_original
    from tribunal.tasks import SupersededDelivery
    settings.MEDIA_ROOT = tmp_path
    file = ready_application.attachments.first().versions.first()
    write_private_original(private_path(file.object_key), b"retained")
    job = enqueue_cleanup(file.object_key)
    with runtime(people["member"]):
        assert not FileVersion.objects.filter(pk=file.pk).exists()
        with pytest.raises(SupersededDelivery):
            cleanup_orphan(job)
    assert private_path(file.object_key).read_bytes() == b"retained"


def test_restricted_role_checkout_response_can_bind_only_provider_reference(runtime, unpaid_application):
    from unittest.mock import patch
    from types import SimpleNamespace
    from django.test import override_settings
    from tribunal.services.payments import create_checkout

    app = unpaid_application
    with runtime(app.owner), override_settings(STRIPE_SECRET_KEY="test-key"), patch(
        "stripe.checkout.Session.create", return_value=SimpleNamespace(id="cs_created_rls", url="https://checkout.stripe.com/test")
    ):
        result = create_checkout(app.owner, app.pk, {"accepted": True, "name": "John Smith"}, "https://example.test", expected_version=1)
        assert result["checkout_url"] == "https://checkout.stripe.com/test"


def test_planned_reschedule_and_private_response_under_non_owner_role(runtime, ready_application, people):
    from datetime import date, datetime, timezone as tz
    from django.db import DatabaseError
    from tribunal.services import council
    from tribunal.services.communications import send_message
    from tribunal.models import TestimonyAppointmentVersion, AgendaTransferEvent, Message, AppointmentResponse

    app = ready_application
    submit_application(app.owner, app.pk, "transfer-rls", {"accepted": True, "name": "John Smith"})
    app.refresh_from_db()
    with runtime(people["admin"]):
        council.assign_case(people["admin"], app.case_id, people["member"].pk, people["president"].pk)
        source = council.create_session(people["admin"], date(2031, 1, 2))
        source_id = source.pk
        item = council.place_agenda(people["admin"], source.pk, app.case_id)
        council.record_attendance(people["admin"], source.pk, people["member"].pk, True)
        appointment = council.schedule_testimony(people["admin"], item.pk, app.party_id,
            datetime(2031, 1, 2, 18, tzinfo=tz.utc), datetime(2031, 1, 2, 19, tzinfo=tz.utc), "Private instructions")
        message = send_message(people["admin"], app.case_id, "Retained body", [app.party_id], "after_session", source.pk)
        target = council.reschedule_session(people["admin"], source.pk, date(2031, 1, 3), {
            str(appointment.pk): {"starts_at": datetime(2031, 1, 3, 18, tzinfo=tz.utc), "ends_at": datetime(2031, 1, 3, 19, tzinfo=tz.utc)}}, "Move meeting")
        assert not council.CouncilSession.objects.filter(pk=source_id).exists()
        assert AgendaTransferEvent.objects.count() == 1
        assert Message.objects.get(pk=message.pk).session_id == target.pk
    with runtime(app.owner):
        own = council.own_testimony(app.owner)["items"][0]
        assert own["version"] == 2 and own["can_respond"]
        assert TestimonyAppointmentVersion.objects.count() == 2
        assert not AgendaTransferEvent.objects.exists()
        assert not council.AgendaItem.objects.exists()
        response = council.respond_testimony(app.owner, appointment.pk, 2, "confirm")
        assert AppointmentResponse.objects.get(pk=response.pk).version == 2
    with pytest.raises(DatabaseError), runtime(people["admin"]):
        Message.objects.filter(pk=message.pk).update(body="Rewritten body")
    with runtime(people["member"]):
        assert TestimonyAppointmentVersion.objects.filter(appointment=appointment).update(instructions="Changed history") == 0
    with pytest.raises(DatabaseError), runtime(people["admin"]):
        council.TestimonyAppointment.objects.create(agenda=target.agenda.get(), party_id=app.party_id,
            starts_at=datetime(2031, 1, 3, 18, tzinfo=tz.utc), ends_at=datetime(2031, 1, 3, 19, tzinfo=tz.utc), instructions="Overlap")
    with runtime(people["admin"]):
        council.close_session(people["admin"], target.pk)
    with runtime(app.owner):
        assert not council.own_testimony(app.owner)["items"][0]["can_respond"]


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


def test_f08_raw_sources_exclude_returned_corrections(runtime, ready_application, people, settings):
    from tests.test_returned_privacy import correction
    settings.CTM_SCAN_REQUIRED = False
    app, formal, draft, old, new = correction(ready_application, people)
    derivative = DocumentText.objects.create(file=new, text="Private pending correction", language="en")
    for role in ["member", "secretary", "admin"]:
        with runtime(people[role]):
            assert AnswerRevision.objects.filter(pk=formal.revision_id).exists()
            assert not AnswerRevision.objects.filter(pk=draft.pk).exists()
            assert FileVersion.objects.filter(pk=old.pk).exists()
            assert not FileVersion.objects.filter(pk=new.pk).exists()
            assert not FileTechnicalEvent.objects.filter(file_id=new.pk).exists()
            assert not DocumentText.objects.filter(pk=derivative.pk).exists()
            assert not AuditEvent.objects.filter(source_id__in=[draft.pk, new.pk]).exists()
    with runtime(app.owner):
        assert AnswerRevision.objects.filter(pk=draft.pk).exists()
        assert FileVersion.objects.filter(pk=new.pk).exists()
    submit_application(app.owner, app.pk, "f08-rls-resubmit", expected_version=app.current_version)
    with runtime(people["member"]):
        assert AnswerRevision.objects.filter(pk=draft.pk).exists()
        assert FileVersion.objects.filter(pk=new.pk).exists()
        assert DocumentText.objects.filter(pk=derivative.pk).exists()


def test_template_library_raw_role_privacy_and_retained_versions(runtime, people):
    from tribunal.models import ReportTemplate, TemplateVersion, ReportQuestion
    from tribunal.services.configuration import create_template, publish_personal_template, retire_template
    from django.db import DatabaseError
    question = ReportQuestion.objects.create(code="raw-library", version=1, category="test", wording_en="Question")
    with runtime(people["member"]):
        personal = create_template(people["member"], "Private template", [question.code])
        assert TemplateVersion.objects.filter(template=personal).exists()
    with runtime(people["president"]):
        assert not ReportTemplate.objects.filter(pk=personal.pk).exists()
        assert not TemplateVersion.objects.filter(template_id=personal.pk).exists()
    with pytest.raises(DatabaseError), runtime(people["member"]):
        ReportTemplate.objects.create(title="Forged shared template", shared=True)
    with runtime(people["secretary"]):
        shared = publish_personal_template(people["secretary"], personal.pk)
    with runtime(people["president"]):
        assert ReportTemplate.objects.filter(pk=shared.pk).exists()
        assert TemplateVersion.objects.filter(template_id=shared.pk).exists()
    with runtime(people["member"]):
        assert TemplateVersion.objects.filter(template=personal).update(questions=[]) == 0
        assert TemplateVersion.objects.get(template=personal).questions[0]["code"] == question.code
    with pytest.raises(DatabaseError), runtime(people["member"]):
        ReportTemplate.objects.filter(pk=personal.pk).update(owner=people["president"])
    with runtime(people["member"]):
        retire_template(people["member"], personal.pk)
        assert TemplateVersion.objects.filter(template=personal).exists()
    with pytest.raises(DatabaseError), runtime(people["member"]):
        ReportTemplate.objects.filter(pk=personal.pk).update(retired=False)
    with runtime(people["applicant"]):
        assert not ReportTemplate.objects.exists() and not TemplateVersion.objects.exists()


def test_assessment_metadata_does_not_grant_raw_medical_scope(runtime, ready_application, people):
    from tribunal.services.reports import create_request
    app = ready_application
    submit_application(app.owner, app.pk, "assessment-status", {"accepted": True, "name": "John Smith"})
    app.refresh_from_db()
    request = create_request(people["admin"], app.proceeding_id, app.party_id, "medical", "Assessment", [])
    file = app.attachments.first().versions.first()
    release = MedicalRelease.objects.create(request=request, subject=app.owner, signature=file,
        declaration=QuestionnaireVersion.objects.get(purpose="medical_release", published=True),
        scope={"council": False, "private_note": "Private consent"})
    with runtime(people["member"]):
        assert not MedicalRelease.objects.filter(pk=release.pk).exists()
        with connection.cursor() as cursor:
            cursor.execute("SELECT public.ctm_assessment_release_metadata(%s)", [str(request.pk)])
            import json
            value = cursor.fetchone()[0]
            result = json.loads(value) if isinstance(value, str) else value
            assert result == {"release_status": "out_of_scope", "release_scope": {"council": False}}
    for actor in [app.owner, None]:
        with runtime(actor), connection.cursor() as cursor:
            cursor.execute("SELECT public.ctm_assessment_release_metadata(%s)", [str(request.pk)])
            value = cursor.fetchone()[0]
            assert value in [{}, "{}"]


def test_f08_withdrawn_detail_and_list_fall_back_when_rls_hides_current(runtime, ready_application, people, settings, client):
    from tests.test_returned_privacy import correction, login
    from tribunal.services.decisions import withdraw_application
    settings.CTM_SCAN_REQUIRED = False
    app, formal, draft, old, new = correction(ready_application, people)
    withdraw_application(app.owner, app.pk)
    login(client, people["secretary"])
    with runtime(people["secretary"]):
        assert not AnswerRevision.objects.filter(pk=draft.pk).exists()
        detail = client.get(f"/api/applications/{app.pk}/").json()
        listing = client.get("/api/applications/").json()["items"]
        row = next(item for item in listing if item["id"] == str(app.pk))
        for item in [detail, row]:
            assert item["answers"] == formal.revision.answers and item["version"] == formal.revision.number


def test_assessment_parent_scope_is_enforced_for_raw_database_writes(runtime, ready_application, people):
    from tribunal.models import ReportRequest, Report
    from tribunal.services.reports import create_request
    from django.db import DatabaseError
    app = ready_application
    submit_application(app.owner, app.pk, "assessment-parent", {"accepted": True, "name": "John Smith"})
    app.refresh_from_db()
    assessment = create_request(people["admin"], app.proceeding_id, app.party_id, "medical", "Assessment", [])
    parent = Report.objects.create(request=assessment, author=app.owner)
    with pytest.raises(DatabaseError), runtime(people["admin"]):
        ReportRequest.objects.create(case=app.case, proceeding=app.proceeding, subject=app.party,
            author=people["admin"], kind="interview", title="Forbidden followup", parent_report=parent)
    with pytest.raises(DatabaseError), runtime(people["admin"]):
        ReportRequest.objects.filter(pk=assessment.pk).update(kind="interview")
    ordinary = create_request(people["admin"], app.proceeding_id, app.party_id, "interview", "Interview", [])
    with runtime(people["admin"]):
        assert Report.objects.filter(pk=parent.pk).update(request=ordinary) == 0
    with runtime(people["admin"]):
        followup = create_request(people["admin"], app.proceeding_id, app.party_id, "psychological", "Permitted", [], parent_id=parent.pk)
        assert followup.parent_report_id == parent.pk


def test_reference_rows_use_separate_questionnaire_question_and_settings_permissions(runtime, people):
    from tribunal.models import SettingRevision, ReportQuestion
    unpublished = QuestionnaireVersion.objects.create(purpose="petition", number=2, definition={})
    question = ReportQuestion.objects.create(code="reference-private", version=1, category="test", wording_en="Question")
    setting = SettingRevision.objects.create(key="tribunal_contact", number=1, value={"display": "Test contact"}, actor=people["admin"])
    with runtime(people["applicant"]):
        assert QuestionnaireVersion.objects.filter(published=True).count() == 3
        assert not QuestionnaireVersion.objects.filter(pk=unpublished.pk).exists()
        assert not ReportQuestion.objects.exists() and not SettingRevision.objects.exists()
    with runtime(people["member"]):
        assert ReportQuestion.objects.filter(pk=question.pk).exists()
        assert not SettingRevision.objects.exists()
        assert not QuestionnaireVersion.objects.filter(pk=unpublished.pk).exists()
    with runtime(people["secretary"]):
        assert SettingRevision.objects.filter(pk=setting.pk).exists()
        assert QuestionnaireVersion.objects.filter(pk=unpublished.pk).exists()
    with runtime():
        assert not QuestionnaireVersion.objects.exists() and not ReportQuestion.objects.exists() and not SettingRevision.objects.exists()


def test_reference_writes_reject_forged_actor_secret_payloads_and_retained_history_changes(runtime, people):
    from tribunal.models import SettingRevision, ReportQuestion
    from tribunal.services.configuration import save_setting
    from django.db import DatabaseError
    with runtime(people["secretary"]):
        setting = save_setting(people["secretary"], "tribunal_contact", {"display": "Test contact"})
    with pytest.raises(DatabaseError), runtime(people["member"]):
        ReportQuestion.objects.create(code="forged-question", version=1, category="test", wording_en="Question")
    with pytest.raises(DatabaseError), runtime(people["secretary"]):
        SettingRevision.objects.create(key="tribunal_contact", number=2, value={}, actor=people["admin"])
    with pytest.raises(DatabaseError), runtime(people["admin"]):
        SettingRevision.objects.create(key="translation_routing", number=1,
            value={"nested": [{"Client_Secret": "synthetic-rejected-value"}]}, actor=people["admin"])
    with pytest.raises(DatabaseError), runtime(people["admin"]):
        QuestionnaireVersion.objects.create(purpose="petition", number=2, published=True, definition={}, declaration_en="Test", declaration_ar="")
    with runtime(people["secretary"]):
        assert SettingRevision.objects.filter(pk=setting.pk).update(value={}) == 0
        assert SettingRevision.objects.filter(pk=setting.pk).delete()[0] == 0
        assert SettingRevision.objects.get(pk=setting.pk).value == {"display": "Test contact"}


def test_f15_dual_assignment_and_revocation_under_real_runtime_role(runtime, ready_application, people, settings):
    from tribunal.models import CaseAssignment, StaffRole, StaffMembership
    from tribunal.services.staff_roles import create_tribunal, grant_assignment_presidency, revoke_assignment_authority
    from tribunal.services.council import assign_case
    from django.core.exceptions import PermissionDenied
    app = ready_application
    submit_application(app.owner, app.pk, "f15-rls", {"accepted": True, "name": "John Smith"})
    app.refresh_from_db()
    actor = people["admin"]
    with runtime(actor):
        tribunal = create_tribunal(actor, "RLS", "Runtime test institution")
    settings.CTM_TRIBUNAL_ID = str(tribunal.pk)
    with runtime(actor):
        role = grant_assignment_presidency(actor, actor.pk, tribunal.pk)
        record = assign_case(actor, app.case_id, people["member"].pk, actor.pk)
        assert record.president_id == record.actor_id == actor.pk
        assert StaffRole.objects.get(pk=role.pk).granted_by_id == actor.pk
        assert StaffMembership.objects.get(pk=role.membership_id).appointed_by_id == actor.pk
        revoke_assignment_authority(actor, role.pk)
    with pytest.raises(PermissionDenied), runtime(actor):
        assign_case(actor, app.case_id, people["member"].pk, actor.pk)
    with runtime(people["member"]):
        assert CaseAssignment.objects.get(pk=record.pk).president_id == actor.pk


def test_f15_raw_grants_cannot_forge_authority_or_rewrite_history(runtime, people, settings):
    from tribunal.models import Tribunal, StaffRole, StaffMembership
    from tribunal.services.staff_roles import create_tribunal, grant_assignment_presidency, revoke_assignment_authority
    from tribunal.db.context import database_actor
    from django.db import DatabaseError
    from django.utils import timezone
    actor = people["admin"]
    tribunal = create_tribunal(actor, "RAW", "Raw test institution")
    settings.CTM_TRIBUNAL_ID = str(tribunal.pk)
    role = grant_assignment_presidency(actor, actor.pk, tribunal.pk)
    for user in [None, people["applicant"]]:
        with runtime(user):
            assert not Tribunal.objects.exists() and not StaffMembership.objects.exists() and not StaffRole.objects.exists()
    with pytest.raises(DatabaseError), runtime(people["member"]), database_actor(people["member"]):
        StaffRole.objects.create(membership_id=role.membership_id, role="member", granted_by=people["member"])
    with pytest.raises(DatabaseError), runtime(actor), database_actor(actor):
        StaffMembership.objects.create(account=people["member"], tribunal=tribunal, appointed_by=people["secretary"])
    with pytest.raises(DatabaseError), runtime(actor), database_actor(actor):
        StaffMembership.objects.create(account=people["applicant"], tribunal=tribunal, appointed_by=actor)
    with pytest.raises(DatabaseError), runtime(actor), database_actor(actor):
        StaffRole.objects.filter(pk=role.pk).update(granted_by=people["secretary"])
    with runtime(actor):
        revoke_assignment_authority(actor, role.pk)
    with pytest.raises(DatabaseError), runtime(actor), database_actor(actor):
        StaffRole.objects.filter(pk=role.pk).update(revoked_at=None)
    with pytest.raises(DatabaseError), runtime(actor), database_actor(actor):
        StaffMembership.objects.filter(pk=role.membership_id).update(account=people["member"])
    with runtime(actor):
        assert StaffRole.objects.filter(pk=role.pk).delete()[0] == 0
        assert StaffMembership.objects.filter(pk=role.membership_id).exists()


def test_f15_raw_assignment_rejects_revoked_cross_tribunal_or_ungranted_president(runtime, ready_application, people, settings):
    from tribunal.models import CaseAssignment
    from tribunal.services.staff_roles import create_tribunal, grant_assignment_presidency, revoke_assignment_authority
    from tribunal.db.context import database_actor
    from django.db import DatabaseError
    app = ready_application
    submit_application(app.owner, app.pk, "f15-raw-assignment", {"accepted": True, "name": "John Smith"})
    app.refresh_from_db()
    actor = people["admin"]
    tribunal = create_tribunal(actor, "ONE", "Test institution one")
    other = create_tribunal(actor, "TWO", "Test institution two")
    settings.CTM_TRIBUNAL_ID = str(tribunal.pk)
    with pytest.raises(DatabaseError), runtime(actor), database_actor(actor):
        CaseAssignment.objects.create(case=app.case, member=people["member"], president=actor, actor=actor)
    role = grant_assignment_presidency(actor, actor.pk, tribunal.pk)
    settings.CTM_TRIBUNAL_ID = str(other.pk)
    with pytest.raises(DatabaseError), runtime(actor), database_actor(actor):
        CaseAssignment.objects.create(case=app.case, member=people["member"], president=actor, actor=actor)
    settings.CTM_TRIBUNAL_ID = str(tribunal.pk)
    revoke_assignment_authority(actor, role.pk)
    with pytest.raises(DatabaseError), runtime(actor), database_actor(actor):
        CaseAssignment.objects.create(case=app.case, member=people["member"], president=actor, actor=actor)


def test_f15_primary_president_records_same_person_under_explicit_runtime_assignment_role(runtime, ready_application, people, settings):
    from tribunal.services.staff_roles import create_tribunal, grant_assignment_authority
    from tribunal.services.council import assign_case
    app = ready_application
    submit_application(app.owner, app.pk, "f15-reverse-roles", {"accepted": True, "name": "John Smith"})
    app.refresh_from_db()
    institution = create_tribunal(people["admin"], "REVERSE", "Reverse role test")
    settings.CTM_TRIBUNAL_ID = str(institution.pk)
    with runtime(people["admin"]):
        grant_assignment_authority(people["admin"], people["president"].pk, institution.pk, "admin")
    with runtime(people["president"]):
        record = assign_case(people["president"], app.case_id, people["member"].pk, people["president"].pk)
        assert record.actor_id == record.president_id == people["president"].pk


def test_f12_full_closed_intake_and_assigned_result_under_runtime_role(runtime, ready_application, people):
    from tests.test_closed_case_intake import prepare, present
    from tribunal.services.council import assign_case
    from tribunal.services.decisions import withdraw_application, decide_appeal, add_appeal_information
    from tribunal.models import Party, AppealDisposition, AppealSupplement, OpenCaseClaim
    app = ready_application
    submit_application(app.owner, app.pk, "f12-raw-original", {"accepted": True, "name": "John Smith"})
    app.refresh_from_db()
    assign_case(people["admin"], app.case_id, people["member"].pk, people["president"].pk)
    spouse = Account.objects.create_user(email="f12-runtime@example.test", email_verified=True)
    Party.objects.create(case=app.case, account=spouse, person=spouse.person, slot="B", participating=False)
    withdraw_application(app.owner, app.pk)
    app.case.refresh_from_db()
    with runtime(spouse):
        filing = prepare(spouse, app.case, people, waive=False)
    from tribunal.services.applications import waive_fee
    with runtime(people["admin"]):
        waive_fee(people["admin"], filing.pk)
    with runtime(spouse):
        submit_application(spouse, filing.pk, "f12-runtime-filing", {"accepted": True, "name": "Jane Smith"})
        extra = add_appeal_information(spouse, filing.pk, "Additional facts")
    with runtime(app.owner):
        assert not Application.objects.filter(pk=filing.pk).exists()
        assert not AppealSupplement.objects.filter(pk=extra.pk).exists()
    with runtime(people["member"]):
        assert AppealSupplement.objects.filter(pk=extra.pk).exists()
    # Session/attendance writers and the assigned presenter keep their own actors.
    from tribunal.services.council import create_session, place_agenda, record_attendance, hear_case
    from datetime import date
    with runtime(people["admin"]):
        session = create_session(people["admin"], date(2031, 1, 7))
        record_attendance(people["admin"], session.pk, people["member"].pk, True)
    with runtime(people["member"]):
        item = place_agenda(people["member"], session.pk, app.case_id)
        hearing = hear_case(people["member"], item.pk)
        result = decide_appeal(people["member"], filing.pk, hearing.pk, "accept")
        assert AppealDisposition.objects.get(pk=result.pk).actor_id == people["member"].pk
    app.case.refresh_from_db(); app.proceeding.refresh_from_db(); filing.refresh_from_db()
    assert app.case.status == "open" and app.proceeding.status == "closed"
    assert filing.status == "accepted" and filing.proceeding_id is None
    assert OpenCaseClaim.objects.get(person=spouse.person).case_id == app.case_id
    with runtime(app.owner):
        assert not AppealDisposition.objects.filter(application_id=filing.pk).exists()


def test_f12_raw_pending_source_and_result_guards(runtime, ready_application, people):
    from tests.test_closed_case_intake import prepare, present
    from tribunal.services.council import assign_case
    from tribunal.services.decisions import withdraw_application
    from tribunal.models import Party, AppealDisposition
    from django.db import DatabaseError
    original = ready_application
    submit_application(original.owner, original.pk, "f12-guard-original", {"accepted": True, "name": "John Smith"})
    original.refresh_from_db()
    assign_case(people["admin"], original.case_id, people["member"].pk, people["president"].pk)
    spouse = Account.objects.create_user(email="f12-guards@example.test", email_verified=True)
    Party.objects.create(case=original.case, person=spouse.person, account=spouse, slot="B", participating=False)
    withdraw_application(original.owner, original.pk)
    original.case.refresh_from_db()
    app = prepare(spouse, original.case, people)
    submit_application(spouse, app.pk, "f12-guard-filing", {"accepted": True, "name": "Jane Smith"})
    app.refresh_from_db()
    for changes in [{"origin": "portal"}, {"proceeding": original.proceeding},
                    {"current_version": 99}, {"status": "accepted"}]:
        with pytest.raises(DatabaseError), runtime(spouse):
            Application.objects.filter(pk=app.pk).update(**changes)
    with pytest.raises(DatabaseError), runtime(spouse):
        AnswerRevision.objects.create(application=app, number=2, actor=spouse, answers={"new_information": "Overwrite"})
    hearing = present(app, people)
    with pytest.raises(DatabaseError), runtime(spouse):
        AppealDisposition.objects.create(application=app, actor=spouse, hearing=hearing, result="accept")
    with pytest.raises(DatabaseError), runtime(people["member"]):
        AppealDisposition.objects.create(application=app, actor=people["member"], hearing=hearing, result="accept")
    with runtime(people["member"]):
        assert Application.objects.filter(pk=app.pk).update(status="accepted") == 0
    with runtime(people["admin"]):
        assert Application.objects.filter(pk=app.pk).exists()
    original.case.refresh_from_db()
    assert original.case.status == "closed" and not AppealDisposition.objects.filter(application=app).exists()


def test_f12_council_result_context_is_status_only_and_cannot_skip_claims(runtime, ready_application, people):
    from tests.test_closed_case_intake import prepare, present
    from tribunal.services.council import assign_case
    from tribunal.services.decisions import withdraw_application
    from tribunal.models import Party, AppealDisposition
    from tribunal.db.context import database_actor, database_settings
    from django.db import DatabaseError
    from django.utils import timezone
    original = ready_application
    submit_application(original.owner, original.pk, "f12-context-original", {"accepted": True, "name": "John Smith"})
    original.refresh_from_db()
    assign_case(people["admin"], original.case_id, people["member"].pk, people["president"].pk)
    spouse = Account.objects.create_user(email="f12-context@example.test", email_verified=True)
    Party.objects.create(case=original.case, person=spouse.person, account=spouse, slot="B", participating=False)
    withdraw_application(original.owner, original.pk)
    original.case.refresh_from_db()
    app = prepare(spouse, original.case, people)
    submit_application(spouse, app.pk, "f12-context-filing", {"accepted": True, "name": "Jane Smith"})
    hearing = present(app, people)
    context = {"ctm.council_result": str(app.pk), "ctm.result_hearing": str(hearing.pk), "ctm.result_choice": "accept"}
    with pytest.raises(DatabaseError), runtime(people["member"]), database_actor(people["member"]), database_settings(context):
        Application.objects.filter(pk=app.pk).update(last_activity=timezone.now())
    with pytest.raises(DatabaseError), runtime(people["member"]), database_actor(people["member"]), database_settings(context):
        AppealDisposition.objects.create(application=app, hearing=hearing, actor=people["member"], result="accept")
    app.refresh_from_db()
    assert app.status == "submitted" and not AppealDisposition.objects.filter(application=app).exists()


def test_own_released_decree_projection_obeys_recipient_rls(runtime, ready_application, people):
    from tribunal.models import Attachment, FileVersion, FileTechnicalEvent
    from tribunal.services.decisions import record_decision, approve_decision, attest_signature, issue_decree, release_decree
    from tribunal.projections import released_decrees
    app = ready_application
    submit_application(app.owner, app.pk, "own-decree-runtime", {"accepted": True, "name": "John Smith"})
    app.refresh_from_db()
    decision = record_decision(people["admin"], app.proceeding_id, "diss-applicant", "Grounds", {str(app.party_id): "certificate"})
    approve_decision(people["president"], decision.pk)
    attachment = Attachment.objects.create(case=app.case, proceeding=app.proceeding, category="DEC", visibility="council")
    file = FileVersion.objects.create(attachment=attachment, number=1, object_key="rls/own-release.pdf",
        original_name="signed.pdf", display_name="signed.pdf", mime_type="application/pdf", byte_count=5,
        sha256="d"*64, actor=people["admin"])
    FileTechnicalEvent.objects.create(file=file, task="scan", result="clean")
    attest_signature(people["president"], file.pk, people["president"].pk, "signed_scan", {"confirmed_signed": True})
    decree = issue_decree(people["admin"], decision.pk, file.pk, people["president"].pk)
    with runtime(app.owner):
        assert released_decrees(app.case, app.owner) == []

    with runtime(people["secretary"]):
        release_decree(people["secretary"], decree.pk, app.party_id)
    with runtime(app.owner):
        rows = released_decrees(app.case, app.owner)
        assert len(rows) == 1 and rows[0]["signed_file"]["id"] == str(file.pk)
    with runtime(people["secretary"]):
        release_decree(people["secretary"], decree.pk, app.party_id, "withdraw")
    with runtime(app.owner):
        assert released_decrees(app.case, app.owner) == []


def test_request_privacy_raw_closure_and_subject_scope(runtime, ready_application, people):
    from tests.test_own_requests import sent
    from tribunal.models import ReportRequest, Party
    from tribunal.services.reports import create_request
    from tribunal.services.decisions import close_case
    app = ready_application
    submit_application(app.owner, app.pk, "request-rls", {"accepted": True, "name": "John Smith"})
    app.refresh_from_db()
    row = sent(app, people)
    draft = create_request(people["admin"], app.proceeding_id, app.party_id, "intake", "Unsent private", [])
    interview = sent(app, people, "interview")
    spouse = Account.objects.create_user(email="request-spouse@example.test", email_verified=True)
    Party.objects.create(case=app.case, account=spouse, person=spouse.person, slot="B")
    with runtime(app.owner):
        assert list(ReportRequest.objects.values_list("pk", flat=True)) == [row.pk]
    with runtime(spouse):
        assert not ReportRequest.objects.exists()
    with runtime():
        assert not ReportRequest.objects.exists()
    with runtime(people["admin"]):
        close_case(people["admin"], app.case, "synthetic_close")
    with runtime(app.owner):
        assert list(ReportRequest.objects.values_list("pk", flat=True)) == [row.pk]
    with runtime(people["member"]):
        assert set(ReportRequest.objects.values_list("pk", flat=True)) == {row.pk, draft.pk, interview.pk}


def test_own_request_completion_and_consent_under_runtime_role(runtime, ready_application, people):
    from tests.test_own_requests import sent, consent, sign
    from tribunal.services.reports import complete_request
    from tribunal.services.request_contracts import own_request_data, request_version
    from tribunal.services.files import request_file_listing
    from tribunal.models import Report, ReportRevision
    from django.db import DatabaseError
    app = ready_application
    submit_application(app.owner, app.pk, "consent-rls", {"accepted": True, "name": "John Smith"})
    app.refresh_from_db()
    row = sent(app, people, "medical")
    signature = consent(app, row)
    with runtime(app.owner):
        release = sign(app, row, signature)
        assert own_request_data(row, app.owner)["signed_releases"][0]["id"] == str(release.pk)
        assert request_file_listing(app.owner, row.pk)["items"][0]["purpose"] == "consent"
    ordinary = sent(app, people)
    with runtime(app.owner):
        report = complete_request(app.owner, ordinary.pk, {"text": "Own immutable response"}, expected_version=request_version(ordinary))
        assert complete_request(app.owner, ordinary.pk, {"text": "Own immutable response"}).pk == report.pk
        assert Report.objects.get(pk=report.pk).author_id == app.owner.pk
    with pytest.raises(DatabaseError), runtime(app.owner):
        ReportRevision.objects.create(report=report, number=2, actor=app.owner, answers={"text": "overwrite"})
    with pytest.raises(DatabaseError), runtime(app.owner):
        MedicalRelease.objects.create(request=row, subject=app.owner, signature=signature,
            declaration=release.declaration, scope={"council": True})
    with pytest.raises(DatabaseError), runtime(people["admin"]):
        from tribunal.models import ReportRequest
        ReportRequest.objects.filter(pk=ordinary.pk).update(instructions="rewrite sent request")
    with runtime(people["admin"]):
        assert Report.objects.filter(pk=report.pk).update(author=people["admin"]) == 0
    with pytest.raises(DatabaseError), transaction.atomic():
        Report.objects.filter(pk=report.pk).update(author=people["admin"])


def test_external_request_read_save_submit_under_runtime_role(runtime, ready_application, people, client):
    from tribunal.services.reports import create_request, send_request
    from tribunal.models import ReportRequest, Report
    app = ready_application
    submit_application(app.owner, app.pk, "external-request-rls", {"accepted": True, "name": "John Smith"})
    app.refresh_from_db()
    with runtime(people["admin"]):
        row = create_request(people["admin"], app.proceeding_id, app.party_id, "external_priest", "External testimony", [])
        token = send_request(people["admin"], row.pk)
    url = f"/external/reports/{row.pk}/"
    with runtime():
        assert client.get(url, HTTP_AUTHORIZATION="Bearer invalid").status_code == 403
        assert client.get(url, HTTP_AUTHORIZATION=f"Bearer {token}").status_code == 200
        assert client.post(url, {"action": "save", "answers": {"text": "Saved"}}, content_type="application/json", HTTP_AUTHORIZATION=f"Bearer {token}").status_code == 200
        response = client.post(url, {"answers": {"text": "Final"}}, content_type="application/json", HTTP_AUTHORIZATION=f"Bearer {token}")
        assert response.status_code == 201
        assert client.get(url, HTTP_AUTHORIZATION=f"Bearer {token}").status_code == 403
        assert not ReportRequest.objects.exists() and not Report.objects.exists()


def test_call_record_runtime_scope_and_retained_provenance(runtime, ready_application, people):
    from tribunal.models import CallRecord, Party
    from tribunal.services.communications import log_call
    from tribunal.services.decisions import close_case
    from django.utils import timezone
    from django.db import DatabaseError
    app = ready_application
    submit_application(app.owner, app.pk, "call-runtime", {"accepted": True, "name": "John Smith"})
    app.refresh_from_db()
    with runtime(people["admin"]):
        record = log_call(people["admin"], app.case_id, app.party_id, timezone.now(), "Reached", "Synthetic private call")
    with runtime(app.owner):
        assert not CallRecord.objects.exists()
    with runtime():
        assert not CallRecord.objects.exists()
    with runtime(people["member"]):
        assert CallRecord.objects.get(pk=record.pk).actor_id == people["admin"].pk
    for actor in [app.owner, people["member"]]:
        with pytest.raises(DatabaseError), runtime(actor):
            CallRecord.objects.create(case=app.case, party=app.party, actor=actor, occurred_at=timezone.now(), outcome="Forged")
    with pytest.raises(DatabaseError), runtime(people["admin"]):
        CallRecord.objects.create(case=app.case, party=app.party, actor=people["member"], occurred_at=timezone.now(), outcome="Wrong actor")
    with runtime(people["admin"]):
        assert CallRecord.objects.filter(pk=record.pk).update(notes="rewrite") == 0
        assert CallRecord.objects.filter(pk=record.pk).delete()[0] == 0
    close_case(people["admin"], app.case, "synthetic_close")
    with runtime(people["secretary"]):
        assert log_call(people["secretary"], app.case_id, app.party_id, timezone.now(), "Closed-case communication").pk


def test_legacy_string_medical_consent_does_not_grant_council_content(runtime, ready_application, people):
    from tests.test_own_requests import sent, consent
    from tribunal.models import Report, ReportRevision, MedicalRelease
    from tribunal.services.files import authorized_file
    from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
    app = ready_application
    submit_application(app.owner, app.pk, "strict-medical-scope", {"accepted": True, "name": "John Smith"})
    app.refresh_from_db()
    row = sent(app, people, "medical")
    file = consent(app, row, category="REPORT")
    release = MedicalRelease.objects.create(request=row, subject=app.owner, signature=file,
        declaration=QuestionnaireVersion.objects.get(purpose="medical_release"), scope={"council": "true"})
    report = Report.objects.create(request=row, author=app.owner)
    revision = ReportRevision.objects.create(report=report, number=1, actor=app.owner, answers={"private": "Synthetic protected narrative"})
    with runtime(people["admin"]):
        assert not MedicalRelease.objects.filter(pk=release.pk).exists()
        assert not ReportRevision.objects.filter(pk=revision.pk).exists()
        assert not FileVersion.objects.filter(pk=file.pk).exists()
        with pytest.raises((ObjectDoesNotExist, PermissionDenied)):
            authorized_file(people["admin"], file.pk)
    with runtime(app.owner):
        assert MedicalRelease.objects.get(pk=release.pk).scope == {"council": "true"}
        assert ReportRevision.objects.filter(pk=revision.pk).exists()


def test_provider_checkout_resume_binding_under_real_runtime_role(runtime, unpaid_application, settings):
    from tests.test_backend_followups import provider_checkout
    from tribunal.services.payments import own_pending_checkout
    from tribunal.models import CheckoutIntent
    from django.db import DatabaseError
    app = unpaid_application
    with runtime(app.owner):
        intent, _ = provider_checkout(app, settings)
        assert own_pending_checkout(app, app.owner)["pending_checkout"]["id"] == str(intent.pk)
    with pytest.raises(DatabaseError), runtime(app.owner):
        CheckoutIntent.objects.filter(pk=intent.pk).update(checkout_url="https://checkout.stripe.com/c/other")
    with pytest.raises(DatabaseError), runtime(app.owner):
        CheckoutIntent.objects.create(application=app, revision=intent.revision,
            checkout_url="https://checkout.stripe.com/c/forged")


def test_media_exact_review_and_attempt_isolation_under_runtime_role(runtime, ready_application, people):
    from tests.test_backend_followups import recorded
    from tests.test_media_contract import output
    from tribunal.models import Recording, ProcessingRun, TranscriptRevision, TranscriptReview
    from tribunal.services.reports import finalize_recording, review_transcript
    from tribunal.services.media import retry_processing, report_recordings
    from django.db import DatabaseError
    app = ready_application
    submit_application(app.owner, app.pk, "media-runtime", {"accepted": True, "name": "John Smith"})
    app.refresh_from_db()
    with runtime(people["admin"]):
        recording, report = recorded(app, people)
        run = finalize_recording(people["admin"], recording.pk)
    for actor in [None, app.owner]:
        with runtime(actor):
            assert not Recording.objects.exists() and not ProcessingRun.objects.exists()
            assert not TranscriptRevision.objects.exists() and not TranscriptReview.objects.exists()
    ProcessingRun.objects.filter(pk=run.pk).update(state="completed")
    revision = TranscriptRevision.objects.create(recording=recording, run=run, number=1, language="en", text="Synthetic unreviewed output")
    with runtime(people["member"]):
        assert not TranscriptRevision.objects.filter(pk=revision.pk).exists()
        assert report_recordings(people["member"], report.pk)["items"][0]["transcripts"] == []
    with runtime(people["admin"]):
        review = review_transcript(people["admin"], revision.pk)
    with runtime(people["member"]):
        assert TranscriptRevision.objects.get(pk=revision.pk).text == revision.text
        assert TranscriptReview.objects.filter(pk=review.pk).exists()
    newer = TranscriptRevision.objects.create(recording=recording, run=run, number=2, language="en", text="Synthetic new output")
    with runtime(people["member"]):
        assert not TranscriptRevision.objects.filter(pk=newer.pk).exists()
    with pytest.raises(DatabaseError), runtime(people["member"]):
        TranscriptReview.objects.create(revision=newer, actor=people["member"])
    with pytest.raises(DatabaseError), runtime(people["admin"]):
        TranscriptRevision.objects.create(recording=recording, run=run, number=3, language="en", text="App cannot impersonate output processor")
    with runtime(people["admin"]):
        assert ProcessingRun.objects.filter(pk=run.pk).update(state="completed") == 0
    ProcessingRun.objects.filter(pk=run.pk).update(state="failed")
    with runtime(people["admin"]):
        retried = retry_processing(people["admin"], run.pk)
        assert retried.attempt == 2 and retry_processing(people["admin"], run.pk).pk == retried.pk
    assert TranscriptRevision.objects.filter(pk=revision.pk).exists()


def test_pending_link_activation_privacy_and_cancel_under_runtime_role(runtime, ready_application, people):
    from tribunal.services.identity import add_other_party, activate_pending_links, cancel_pending_link
    from tribunal.models import PendingPartyLink, Party
    from django.db import DatabaseError
    app = ready_application
    submit_application(app.owner, app.pk, "pending-rls", {"accepted": True, "name": "John Smith"})
    app.refresh_from_db()
    with runtime(people["secretary"]):
        pending = add_other_party(people["secretary"], app.case_id, "Jane", "Smith", "pending-rls@example.test")
    account = Account.objects.create_user(email="pending-rls@example.test")
    for actor in [None, app.owner, account, people["member"]]:
        with runtime(actor):
            assert not PendingPartyLink.objects.exists()
    Account.objects.filter(pk=account.pk).update(email_verified=True)
    account.refresh_from_db()
    with runtime(account):
        assert PendingPartyLink.objects.get(pk=pending.pk).email == account.email
        linked = activate_pending_links(account)
        assert len(linked) == 1
    assert Party.objects.filter(case=app.case, account=account).count() == 1
    with pytest.raises(DatabaseError), runtime(account):
        PendingPartyLink.objects.filter(pk=pending.pk).update(email="retarget@example.test")
    with runtime(people["admin"]):
        other = add_other_party(people["admin"], app.case_id, "Other", "Person", "cancelled-pending@example.test")
        assert cancel_pending_link(people["admin"], other.pk).state == "cancelled"


def test_scoped_processing_status_and_attributed_correction_runtime(runtime, ready_application, people):
    from tests.test_backend_followups import recorded
    from tribunal.services.reports import finalize_recording, review_transcript
    from tribunal.services.media import correct_transcript, report_recordings, transcript_for
    from tribunal.models import ProcessingRun, TranscriptRevision
    app = ready_application
    submit_application(app.owner, app.pk, "correction-rls", {"accepted": True, "name": "John Smith"})
    app.refresh_from_db()
    recording, report = recorded(app, people)
    run = finalize_recording(people["admin"], recording.pk)
    ProcessingRun.objects.filter(pk=run.pk).update(state="completed", error="Synthetic private diagnostic")
    original = TranscriptRevision.objects.create(recording=recording, run=run, language="en", number=1, text="Synthetic source")
    with runtime(people["admin"]):
        review_transcript(people["admin"], original.pk)
    with runtime(people["member"]):
        assert not ProcessingRun.objects.filter(pk=run.pk).exists()
        assert transcript_for(people["member"], original.pk).text == original.text
        row = report_recordings(people["member"], report.pk)["items"][0]
        assert row["processing"]["state"] == "succeeded" and "diagnostic" not in str(row)
    with runtime(people["admin"]):
        corrected = correct_transcript(people["admin"], original.pk, "Attributed correction", [], 1)
        assert corrected.actor_id == people["admin"].pk
    with runtime(people["member"]):
        assert not TranscriptRevision.objects.filter(pk=corrected.pk).exists()
        assert TranscriptRevision.objects.filter(pk=original.pk).exists()


def test_private_message_acknowledgement_under_runtime_role(runtime, ready_application, people):
    from tribunal.services.communications import send_message, acknowledge_message
    from tribunal.models import MessageRecipient
    app = ready_application
    submit_application(app.owner, app.pk, "message-read-runtime", {"accepted": True, "name": "John Smith"})
    app.refresh_from_db()
    with runtime(people["admin"]):
        message = send_message(people["admin"], app.case_id, "Synthetic private message", [str(app.party_id)], idempotency_key="runtime-message")
    with runtime(app.owner):
        receipt = acknowledge_message(app.owner, message.pk)
        assert receipt.read_at
        assert acknowledge_message(app.owner, message.pk).read_at == receipt.read_at
    with runtime(people["admin"]):
        assert MessageRecipient.objects.filter(pk=receipt.pk).update(read_at=None) == 0


def test_case_number_counter_hidden_and_allocator_context_bound(runtime, ready_application):
    from tribunal.models import CaseNumberCounter
    from tribunal.services.applications import allocate_case_number
    from django.db import DatabaseError
    app = ready_application
    with pytest.raises(DatabaseError), runtime(app.owner):
        allocate_case_number()
    with runtime(app.owner):
        assert not CaseNumberCounter.objects.exists()
        submitted = submit_application(app.owner, app.pk, "bound-counter-runtime", {"accepted": True, "name": "John Smith"})
        assert submitted.application.case_id
        assert not CaseNumberCounter.objects.exists()
