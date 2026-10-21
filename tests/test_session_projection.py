from datetime import date
import pytest
from tribunal.services.council import create_session

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    "role,allowed",
    [("applicant", None), ("member", False), ("admin", True), ("secretary", True)],
)
def test_session_agenda_exposes_attendance_authority(client, people, role, allowed):
    session = create_session(people["admin"], date(2030, 1, 2))
    client.force_login(
        people[role], backend="allauth.account.auth_backends.AuthenticationBackend"
    )
    response = client.get(f"/api/sessions/{session.pk}/agenda/")
    if allowed is None:
        assert response.status_code == 403
    else:
        assert response.status_code == 200
        assert response.json()["session"]["date"] == "2030-01-02"
        assert response.json()["session"]["can_record_attendance"] is allowed


def test_attendance_projection_preserves_deactivated_members(client, people):
    from tribunal.services.council import record_attendance

    session = create_session(people["admin"], date(2030, 1, 2))
    record_attendance(people["admin"], session.pk, people["member"].pk, True)
    people["member"].is_active = False
    people["member"].save(update_fields=["is_active"])
    client.force_login(
        people["admin"], backend="allauth.account.auth_backends.AuthenticationBackend"
    )
    row = client.get(f"/api/sessions/{session.pk}/attendance/").json()["items"][0]
    assert row["member_name"] == "member Test"
    assert row["member_active"] is False
    assert row["present"] is True
