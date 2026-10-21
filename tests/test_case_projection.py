import pytest
from tribunal.services.applications import submit_application
from tribunal.services.council import assign_case

pytestmark = pytest.mark.django_db


def test_case_projection_flags_support_private_message_composition(
    client, ready_application, people
):
    app = ready_application
    submit_application(
        app.owner, app.pk, "projection", {"accepted": True, "name": "John Smith"}
    )
    app.refresh_from_db()
    url = f"/api/cases/{app.case_id}/"
    client.force_login(
        app.owner, backend="allauth.account.auth_backends.AuthenticationBackend"
    )
    own = client.get(url).json()
    assert own["can_message"] is True
    assert own["parties"][0]["is_self"] is True
    assert own["parties"][0]["can_receive"] is True
    assert "email" not in own["parties"][0]
    client.force_login(
        people["member"], backend="allauth.account.auth_backends.AuthenticationBackend"
    )
    assert client.get(url).json()["can_message"] is False
    assign_case(
        people["admin"], app.case_id, people["member"].pk, people["president"].pk
    )
    assigned = client.get(url).json()
    assert assigned["can_message"] is True
    assert assigned["parties"][0]["is_self"] is False
