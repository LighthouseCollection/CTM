"""Real allauth completion after a synthetic, provider-validated response boundary."""
import pytest
from django.urls import include, path
from django.db import connection
from allauth.account.models import EmailAddress
from allauth.socialaccount.models import SocialAccount, SocialApp, SocialLogin
from allauth.socialaccount.providers.microsoft.provider import MicrosoftGraphProvider
from allauth.socialaccount.helpers import complete_social_login
from tribunal.auth import AccountAdapter, provider_identity
from tribunal.models import Account
from tests.test_core_policy_completion import granted_roles

pytestmark = pytest.mark.django_db


def validated_callback(request):
    app = SocialApp(provider="microsoft", client_id="synthetic-client", secret="synthetic-secret")
    login = SocialLogin(
        account=SocialAccount(provider="microsoft", uid="preauthorized-council-subject"),
        provider=MicrosoftGraphProvider(request, app=app),
        email_addresses=[EmailAddress(email="admin@example.test", verified=True, primary=True)],
    )
    login.user = AccountAdapter(request).new_user(request, login)
    login.state = {"process": "login"}
    return complete_social_login(request, login)


urlpatterns = [path("_test/validated-callback/", validated_callback), path("", include("ctm.urls"))]


def test_restricted_microsoft_callback_completes_first_and_existing_login(granted_roles, people, client, settings):
    settings.ROOT_URLCONF = __name__
    settings.MICROSOFT_TENANT_ID = "specific-synthetic-tenant"
    settings.SOCIALACCOUNT_PROVIDERS = {"microsoft": {"APP": {"client_id": "synthetic-client", "secret": "synthetic-secret"}}}
    admin = people["admin"]
    admin.microsoft_subject = "preauthorized-council-subject"
    admin.email_verified = False
    admin.save(update_fields=["microsoft_subject", "email_verified"])
    for _ in range(2):
        with granted_roles("ctm_app", session=True):
            response = client.get("/_test/validated-callback/")
            assert response.status_code == 302, response.content
            assert client.session["_auth_user_id"] == str(admin.pk)
            assert client.get("/api/session/").json()["id"] == str(admin.pk)
            assert not hasattr(response.wsgi_request, "_ctm_provider_scope")
            assert not Account.objects.filter(pk=admin.pk).exists()
            with connection.cursor() as cursor:
                cursor.execute("SELECT current_setting('ctm.provider',true), current_setting('ctm.provider_subject',true)")
                assert all(not value for value in cursor.fetchone())
        client.logout()
    admin.refresh_from_db()
    assert admin.email_verified and admin.last_login is not None
    assert SocialAccount.objects.filter(user=admin, provider="microsoft").count() == 1


@pytest.mark.parametrize("rejection", ["unbound_subject", "inactive", "applicant", "generic_tenant"])
def test_rejected_callback_cannot_install_identity_scope(granted_roles, people, client, settings, rejection):
    settings.ROOT_URLCONF = __name__
    settings.MICROSOFT_TENANT_ID = "specific-synthetic-tenant"
    settings.SOCIALACCOUNT_PROVIDERS = {"microsoft": {"APP": {"client_id": "synthetic-client", "secret": "synthetic-secret"}}}
    admin = people["admin"]
    admin.microsoft_subject = "preauthorized-council-subject"
    if rejection == "unbound_subject":
        admin.microsoft_subject = "different-preauthorized-subject"
    elif rejection == "inactive":
        admin.is_active = False
    elif rejection == "applicant":
        admin.role = "applicant"
    else:
        settings.MICROSOFT_TENANT_ID = "common"
    admin.save()
    with granted_roles("ctm_app", session=True):
        response = client.get("/_test/validated-callback/")
        assert response.status_code == 403
        assert "_auth_user_id" not in client.session
        assert not hasattr(response.wsgi_request, "_ctm_provider_scope")
        assert not Account.objects.filter(pk=admin.pk).exists()
        with connection.cursor() as cursor:
            cursor.execute("SELECT current_setting('ctm.provider',true), current_setting('ctm.provider_subject',true)")
            assert all(not value for value in cursor.fetchone())
    assert not SocialAccount.objects.exists()


def test_original_hook_lifetime_reproduces_signup_closed(granted_roles, people, client, settings, monkeypatch):
    settings.ROOT_URLCONF = __name__
    settings.MICROSOFT_TENANT_ID = "specific-synthetic-tenant"
    settings.SOCIALACCOUNT_PROVIDERS = {"microsoft": {"APP": {"client_id": "synthetic-client", "secret": "synthetic-secret"}}}
    admin = people["admin"]
    admin.microsoft_subject = "preauthorized-council-subject"
    admin.save(update_fields=["microsoft_subject"])

    def original_hook(self, request, login):
        with provider_identity(login):
            return self._pre_social_login(request, login)

    monkeypatch.setattr(AccountAdapter, "pre_social_login", original_hook)
    with granted_roles("ctm_app", session=True):
        response = client.get("/_test/validated-callback/")
        assert response.status_code == 200
        assert b"Sign Up Closed" in response.content
        assert "_auth_user_id" not in client.session
