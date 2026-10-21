import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from tribunal.models import *
from tribunal.services.applications import submit_application
from tribunal.services.decisions import (
    record_decision,
    approve_decision,
    issue_decree,
    release_decree,
)

pytestmark = pytest.mark.django_db


def test_certificate_hidden_until_release_and_revocable(ready_application, people):
    from tribunal.services.files import authorized_file

    app = ready_application
    submit_application(
        app.owner, app.pk, "issue", {"accepted": True, "name": "John Smith"}
    )
    app.refresh_from_db()
    revision = record_decision(
        people["admin"],
        app.proceeding_id,
        "diss-applicant",
        "Reason",
        {str(app.party_id): "certificate"},
    )
    approve_decision(people["president"], revision.pk)
    attachment = Attachment.objects.create(
        case=app.case, proceeding=app.proceeding, category="DEC", visibility="council"
    )
    file = FileVersion.objects.create(
        attachment=attachment,
        number=1,
        object_key="signed.pdf",
        original_name="signed.pdf",
        display_name="signed.pdf",
        mime_type="application/pdf",
        byte_count=5,
        sha256="d" * 64,
        actor=people["admin"],
    )
    FileTechnicalEvent.objects.create(file=file, task="scan", result="clean")
    from tribunal.services.decisions import attest_signature

    attest_signature(
        people["admin"],
        file.pk,
        people["president"].pk,
        "signed_scan",
        {"confirmed_signed": True},
    )
    decree = issue_decree(people["admin"], revision.pk, file.pk, people["president"].pk)
    app.case.refresh_from_db()
    assert app.case.status == "closed"
    with pytest.raises(PermissionDenied):
        authorized_file(app.owner, file.pk)
    release_decree(people["admin"], decree.pk, app.party_id)
    assert authorized_file(app.owner, file.pk).pk == file.pk
    release_decree(people["secretary"], decree.pk, app.party_id, "withdraw")
    with pytest.raises(PermissionDenied):
        authorized_file(app.owner, file.pk)


def test_case_worker_cannot_issue_decree(ready_application, people):
    with pytest.raises(PermissionDenied):
        issue_decree(
            people["member"],
            "00000000-0000-0000-0000-000000000001",
            "00000000-0000-0000-0000-000000000002",
            people["president"].pk,
        )


def test_sent_report_snapshot_does_not_change_with_new_question_version(
    ready_application, people
):
    from tribunal.services.reports import create_request, send_request

    app = ready_application
    submit_application(
        app.owner, app.pk, "snapshot", {"accepted": True, "name": "John Smith"}
    )
    app.refresh_from_db()
    ReportQuestion.objects.create(
        code="TEST-1", version=1, category="Test", wording_en="Original question"
    )
    request = create_request(
        people["admin"],
        app.proceeding_id,
        app.party_id,
        "intake",
        "Request",
        ["TEST-1"],
    )
    send_request(people["admin"], request.pk)
    ReportQuestion.objects.create(
        code="TEST-1", version=2, category="Test", wording_en="Revised question"
    )
    request.refresh_from_db()
    assert request.questions[0]["en"] == "Original question"
