"""Private draft reads must not reveal existence through a different denial."""
import uuid
import pytest
from tribunal.models import Account
from tests.test_core_policy_completion import granted_roles

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize("suffix", ["", "history/", "files/", "payments/"])
def test_private_draft_and_absent_reads_match_under_app_session(
    granted_roles, ready_application, people, client, suffix
):
    app = ready_application
    client.force_login(app.owner)
    with granted_roles("ctm_app", session=True):
        own = client.get(f"/api/applications/{app.pk}/{suffix}")
        assert own.status_code == 200, own.content
    outsider = Account.objects.create_user(
        email="draft-contract-outsider@example.test", email_verified=True
    )
    for actor in [outsider, *(people[role] for role in ["member", "president", "admin", "secretary"])]:
        client.force_login(actor)
        with granted_roles("ctm_app", session=True):
            private = client.get(f"/api/applications/{app.pk}/{suffix}")
            absent = client.get(f"/api/applications/{uuid.uuid4()}/{suffix}")
            assert private.status_code == absent.status_code == 404
            assert private.content == absent.content == b'{"error": "resource_or_input_invalid"}'
            assert private["Cache-Control"] == absent["Cache-Control"] == "private, no-store"
            directory = client.get("/api/applications/")
            assert directory.status_code == 200, directory.content
            assert str(app.pk) not in [item["id"] for item in directory.json()["items"]]
