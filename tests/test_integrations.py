import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import override_settings
from tribunal.models import (
    Account,
    Notification,
    ReportQuestion,
    SettingRevision,
    DocumentText,
    QuestionnaireVersion,
)

pytestmark = pytest.mark.django_db


def test_shared_settings_reject_applicant_and_secret_material(people):
    from tribunal.services.configuration import save_setting

    with pytest.raises(PermissionDenied):
        save_setting(people["applicant"], "translation_prompt", {"text": "x"})
    with pytest.raises(ValidationError):
        save_setting(people["admin"], "translation", {"api_key": "secret"})
    first = save_setting(people["admin"], "translation_prompt", {"text": "First"})
    second = save_setting(people["secretary"], "translation_prompt", {"text": "Second"})
    assert first.number == 1 and second.number == 2
    first.refresh_from_db()
    assert first.value == {"text": "First"}


def test_template_does_not_publish_from_member_role(people):
    from tribunal.services.configuration import create_template

    with pytest.raises(PermissionDenied):
        create_template(people["member"], "Shared", [], shared=True)
    template = create_template(people["member"], "Personal", [], shared=False)
    assert template.owner_id == people["member"].pk


def test_staff_cannot_get_draft_file_through_search(ready_application, people):
    from tribunal.services.files import authorized_file

    file = ready_application.attachments.first().versions.first()
    DocumentText.objects.create(file=file, engine="test", text="Private draft")
    with pytest.raises(PermissionDenied):
        authorized_file(people["member"], file.pk)


def test_provider_callback_fails_closed_without_specific_tenant(people):
    from types import SimpleNamespace
    from tribunal.auth import AccountAdapter

    social = SimpleNamespace(
        account=SimpleNamespace(provider="microsoft", uid="subject"),
        is_existing=True,
        user=people["admin"],
    )
    with override_settings(MICROSOFT_TENANT_ID="organizations"):
        with pytest.raises(PermissionDenied):
            AccountAdapter().pre_social_login(None, social)


def test_evidence_magic_rejects_disguised_executable():
    from tribunal.services.files import identify

    with pytest.raises(ValidationError):
        identify(b"MZnot-a-pdf")


def test_read_only_external_link_returns_only_necessary_context(
    ready_application, people, client
):
    from tribunal.services.applications import submit_application
    from tribunal.services.reports import create_request, send_request

    submit_application(
        ready_application.owner,
        ready_application.pk,
        "r",
        {"accepted": True, "name": "John Smith"},
    )
    ready_application.refresh_from_db()
    req = create_request(
        people["admin"],
        ready_application.proceeding_id,
        ready_application.party_id,
        "external_priest",
        "Report",
        [],
    )
    token = send_request(people["admin"], req.pk, external_name="Fr. Test")
    response = client.get(
        f"/external/reports/{req.pk}/", HTTP_AUTHORIZATION=f"Bearer {token}"
    )
    assert response.status_code == 200
    data = response.json()
    assert "subject" in data and "application_answers" not in data
