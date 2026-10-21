import pytest
from django.core.exceptions import PermissionDenied
from tribunal.models import *
from tribunal.services.applications import submit_application
from tribunal.services.reports import create_request
from tribunal.services.files import authorized_file

pytestmark = pytest.mark.django_db


def test_release_for_one_request_does_not_disclose_another(ready_application, people):
    app = ready_application
    submit_application(
        app.owner, app.pk, "medical-scope", {"accepted": True, "name": "John Smith"}
    )
    app.refresh_from_db()
    first = create_request(
        people["admin"], app.proceeding_id, app.party_id, "medical", "First", []
    )
    second = create_request(
        people["admin"], app.proceeding_id, app.party_id, "psychological", "Second", []
    )
    signature = app.attachments.first().versions.first()
    declaration = QuestionnaireVersion.objects.get(purpose="medical_release")
    MedicalRelease.objects.create(
        request=first,
        subject=app.owner,
        declaration=declaration,
        signature=signature,
        scope={"council": True},
    )
    attachment = Attachment.objects.create(
        case=app.case,
        proceeding=app.proceeding,
        report_request=second,
        owner=app.owner,
        category="MED",
        visibility="medical",
    )
    file = FileVersion.objects.create(
        attachment=attachment,
        number=1,
        object_key="medical-second",
        original_name="report.pdf",
        display_name="report.pdf",
        mime_type="application/pdf",
        byte_count=1,
        sha256="a" * 64,
    )
    FileTechnicalEvent.objects.create(file=file, task="scan", result="clean")
    with pytest.raises(PermissionDenied):
        authorized_file(people["member"], file.pk)
