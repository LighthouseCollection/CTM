import pytest
from django.utils import timezone
from django.test import override_settings
from tribunal.models import Outbox, Case
from tribunal.tasks import dispatch_outbox

pytestmark = pytest.mark.django_db


@override_settings(EMAIL_HOST="configured-for-test")
def test_digest_is_one_email_not_one_per_edit(people, mailoutbox):
    case = Case.objects.create(number="20261021-40", assigned_member=people["member"])
    for i, kind in enumerate(["answer_changed", "file_uploaded", "appeal_added"]):
        Outbox.objects.create(
            key=f"digest-{i}",
            case=case,
            recipient=people["member"],
            kind=kind,
            due_at=timezone.now(),
        )
    assert dispatch_outbox() == 3
    assert len(mailoutbox) == 1
    assert Outbox.objects.filter(delivered_at__isnull=False).count() == 3


@override_settings(EMAIL_HOST="configured-for-test")
def test_unsent_routine_update_routes_to_current_manager(people, mailoutbox):
    case = Case.objects.create(
        number="20261021-41", assigned_member=people["president"]
    )
    Outbox.objects.create(
        key="old-manager",
        case=case,
        recipient=people["member"],
        kind="answer_changed",
        due_at=timezone.now(),
    )
    dispatch_outbox()
    assert len(mailoutbox) == 1
    assert mailoutbox[0].to == [people["president"].email]


def test_failed_provider_keeps_job_for_retry(people):
    event = Outbox.objects.create(
        key="no-provider", recipient=people["member"], kind="message"
    )
    with override_settings(EMAIL_HOST=""):
        assert dispatch_outbox() == 0
    event.refresh_from_db()
    assert event.delivered_at is None
    assert event.last_error
