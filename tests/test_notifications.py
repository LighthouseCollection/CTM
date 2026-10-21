import json
import pytest
from tribunal.models import Notification

pytestmark = pytest.mark.django_db


def test_notification_inbox_is_private_and_read_timestamp_is_idempotent(client, people):
    own = Notification.objects.create(
        recipient=people["applicant"], key="own", kind="report_requested"
    )
    other = Notification.objects.create(
        recipient=people["member"], key="other", kind="report_received"
    )
    client.force_login(
        people["applicant"],
        backend="allauth.account.auth_backends.AuthenticationBackend",
    )
    listing = client.get("/api/notifications/").json()
    assert [row["id"] for row in listing["items"]] == [str(own.pk)]
    assert listing["unread_count"] == 1
    assert listing["next_offset"] is None
    assert (
        client.post(
            "/api/notifications/",
            data=json.dumps({"id": str(other.pk)}),
            content_type="application/json",
        ).json()["updated"]
        is False
    )
    for _ in range(2):
        client.post(
            "/api/notifications/",
            data=json.dumps({"id": str(own.pk)}),
            content_type="application/json",
        )
        own.refresh_from_db()
        if _ == 0:
            first_read = own.read_at
        else:
            assert own.read_at == first_read
    assert client.get("/api/notifications/").json()["unread_count"] == 0
