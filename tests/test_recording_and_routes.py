import json
import pytest
from tribunal.models import Attachment, FileVersion, FileTechnicalEvent, Recording
from tribunal.services.applications import submit_application
from tribunal.services.reports import (
    create_request,
    send_request,
    complete_request,
    create_recording,
    finalize_recording,
)

pytestmark = pytest.mark.django_db


def test_whole_report_recording_queues_only_after_finalization(
    ready_application, people
):
    app = ready_application
    submit_application(
        app.owner, app.pk, "whole-recording", {"accepted": True, "name": "John Smith"}
    )
    app.refresh_from_db()
    request = create_request(
        people["admin"], app.proceeding_id, app.party_id, "interview", "Interview", []
    )
    send_request(people["admin"], request.pk)
    report = complete_request(
        people["admin"], request.pk, {"answer": "Recorded interview"}
    )
    attachment = Attachment.objects.create(
        case=app.case, proceeding=app.proceeding, visibility="council", category="AUDIO"
    )
    file = FileVersion.objects.create(
        attachment=attachment,
        number=1,
        object_key="whole-report.mp3",
        mime_type="audio/mpeg",
        byte_count=1,
        sha256="c" * 64,
    )
    FileTechnicalEvent.objects.create(file=file, task="scan", result="clean")
    recording = create_recording(
        people["admin"], file.pk, report_id=report.pk, notice_recorded=True
    )
    assert recording.finalized_at is None
    assert file.processingrun_set.count() == 0
    run = finalize_recording(people["admin"], recording.pk)
    assert run.state == "queued"
    assert finalize_recording(people["admin"], recording.pk).pk == run.pk


def test_applicant_cannot_log_internal_calls(client, ready_application):
    app = ready_application
    submit_application(
        app.owner, app.pk, "calls-private", {"accepted": True, "name": "John Smith"}
    )
    app.refresh_from_db()
    client.force_login(
        app.owner, backend="allauth.account.auth_backends.AuthenticationBackend"
    )
    assert client.get(f"/api/cases/{app.case_id}/calls/").status_code == 403
