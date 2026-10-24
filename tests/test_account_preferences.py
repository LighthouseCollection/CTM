import pytest
from tribunal.models import AuditEvent

pytestmark = pytest.mark.django_db


def sign_in(client, account):
    client.force_login(
        account, backend="allauth.account.auth_backends.AuthenticationBackend"
    )


def test_preferences_require_authentication(client):
    assert client.get("/api/account/settings/").status_code == 401


def test_preference_change_is_limited_to_own_language_and_audited(client, people):
    user = people["applicant"]
    sign_in(client, user)
    response = client.post(
        "/api/account/settings/",
        {"ui_language": "ar", "notification_language": "ar"},
        content_type="application/json",
    )
    assert response.status_code == 200
    user.refresh_from_db()
    assert user.ui_language == user.notification_language == "ar"
    assert user.role == "applicant"
    assert client.get("/api/session/").json()["ui_language"] == "ar"
    event = AuditEvent.objects.get(action="account_preferences_changed")
    assert event.actor_id == user.pk
    assert event.metadata["before"]["ui_language"] == "en"
    assert event.metadata["after"]["ui_language"] == "ar"
    people["member"].refresh_from_db()
    assert people["member"].ui_language == "en"


@pytest.mark.parametrize(
    "payload",
    [
        {"ui_language": "fr"},
        {"role": "admin"},
        {"email": "new@example.test"},
        {"ui_language": None},
        {"notification_language": ["ar"]},
        {},
    ],
)
def test_preferences_reject_unknown_fields_and_invalid_languages(
    client, people, payload
):
    sign_in(client, people["applicant"])
    response = client.post(
        "/api/account/settings/", payload, content_type="application/json"
    )
    assert response.status_code == 422
    assert not AuditEvent.objects.filter(action="account_preferences_changed").exists()


def test_account_owner_can_update_own_profile_name_and_receives_an_audit_entry(client, people):
    user = people["member"]
    sign_in(client, user)
    response = client.post(
        "/api/account/settings/",
        {"first_name": "Updated", "last_name": "Member"},
        content_type="application/json",
    )
    assert response.status_code == 200
    user.refresh_from_db()
    assert (user.first_name, user.last_name) == ("Updated", "Member")
    assert response.json()["name"] == "Updated Member"
    event = AuditEvent.objects.get(action="account_profile_changed")
    assert event.actor_id == user.pk


def test_unchanged_preference_does_not_add_history(client, people):
    sign_in(client, people["member"])
    assert (
        client.post(
            "/api/account/settings/",
            {"ui_language": "en"},
            content_type="application/json",
        ).status_code
        == 200
    )
    assert not AuditEvent.objects.filter(action="account_preferences_changed").exists()


def test_session_exposes_signed_in_email_for_header(client, people):
    user = people["member"]
    sign_in(client, user)
    response = client.get("/api/session/")
    assert response.status_code == 200
    assert response.json()["email"] == user.email
