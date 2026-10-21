import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone
from tribunal.models import Application, Notification
from tribunal.services.applications import start_application, submit_application

pytestmark = pytest.mark.django_db


def test_retention_warns_then_expires_only_unsubmitted(people):
    from tribunal.services.retention import process_drafts

    app = start_application(people["applicant"])
    Application.objects.filter(pk=app.pk).update(
        last_activity=timezone.now() - timezone.timedelta(days=174)
    )
    process_drafts()
    assert Notification.objects.filter(
        recipient=app.owner, kind="draft_expiring"
    ).exists()
    Application.objects.filter(pk=app.pk).update(
        last_activity=timezone.now() - timezone.timedelta(days=181)
    )
    process_drafts()
    app.refresh_from_db()
    assert app.status == "expired"


def test_submitted_application_does_not_expire(ready_application):
    from tribunal.services.retention import process_drafts

    app = ready_application
    submit_application(
        app.owner, app.pk, "keep", {"accepted": True, "name": "John Smith"}
    )
    Application.objects.filter(pk=app.pk).update(
        last_activity=timezone.now() - timezone.timedelta(days=500)
    )
    process_drafts()
    app.refresh_from_db()
    assert app.status == "submitted" and app.revisions.count() == 1
