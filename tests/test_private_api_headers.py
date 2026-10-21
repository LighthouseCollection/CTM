import pytest

pytestmark = pytest.mark.django_db


def test_authenticated_and_rejected_api_responses_are_not_cacheable(client, people):
    for signed_in in [False, True]:
        if signed_in:
            client.force_login(
                people["applicant"],
                backend="allauth.account.auth_backends.AuthenticationBackend",
            )
        response = client.get("/api/cases/")
        assert response.status_code == (200 if signed_in else 401)
        assert response["Cache-Control"] == "private, no-store"
        assert response["Referrer-Policy"] == "same-origin"
        assert response["X-Content-Type-Options"] == "nosniff"


@pytest.mark.parametrize(
    "url", ["/api/not-a-route/", "/external/reports/not-an-id/", "/accounts/login/"]
)
def test_private_headers_also_cover_missing_and_capability_pages(client, url):
    response = client.get(url)
    assert response["Cache-Control"] == "private, no-store"
    assert response["Referrer-Policy"] == "same-origin"


def test_csrf_rejections_keep_private_headers():
    from django.test import Client

    response = Client(enforce_csrf_checks=True).post("/api/applications/", data={})
    assert response.status_code == 403
    assert response["Cache-Control"] == "private, no-store"
