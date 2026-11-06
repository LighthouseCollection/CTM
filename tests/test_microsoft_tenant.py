"""#64 / D-0021: a Microsoft sign-in counts only for an account of the configured tenant.

The tenant comes from the id_token in the token-endpoint response (received
directly from login.microsoftonline.com over TLS), never from the email domain.
#65: a refused first binding is the uniform "not allowed" answer, not a 500.
"""
import base64
import json
import time

import pytest
from allauth.account.models import EmailAddress
from allauth.socialaccount.helpers import complete_social_login
from allauth.socialaccount.models import SocialAccount, SocialApp, SocialLogin
from allauth.socialaccount.providers.microsoft.provider import MicrosoftGraphProvider
from allauth.socialaccount.providers.microsoft.views import MicrosoftGraphOAuth2Adapter
from django.core.exceptions import PermissionDenied
from django.test import RequestFactory
from django.urls import include, path, resolve

from tests.test_core_policy_completion import granted_roles  # noqa: F401 (fixture)
from tribunal import auth
from tribunal.auth import AccountAdapter, CouncilMicrosoftAdapter, verified_microsoft_tenant

TENANT = "11111111-2222-3333-4444-555555555555"
FOREIGN = "99999999-8888-7777-6666-555555555555"
CLIENT = "synthetic-client"
SUBJECT = "tenant-check-subject"


def id_token(**overrides):
    claims = {
        "tid": TENANT,
        "iss": f"https://login.microsoftonline.com/{TENANT}/v2.0",
        "aud": CLIENT,
        "oid": SUBJECT,
        "exp": int(time.time()) + 600,
    }
    claims.update(overrides)
    claims = {k: v for k, v in claims.items() if v is not None}
    part = lambda data: base64.urlsafe_b64encode(json.dumps(data).encode()).rstrip(b"=").decode()
    return f"{part({'alg': 'RS256', 'typ': 'JWT'})}.{part(claims)}.synthetic-signature"


@pytest.fixture
def tenant(settings):
    settings.MICROSOFT_TENANT_ID = TENANT
    return TENANT


def test_token_of_the_configured_tenant_is_accepted(tenant):
    assert verified_microsoft_tenant({"id_token": id_token()}, CLIENT, SUBJECT) == TENANT


def test_tenant_comparison_ignores_guid_case(settings):
    settings.MICROSOFT_TENANT_ID = TENANT.upper()
    assert verified_microsoft_tenant({"id_token": id_token()}, CLIENT, SUBJECT) == TENANT


@pytest.mark.parametrize(
    "response",
    [
        pytest.param({"id_token": id_token(tid=FOREIGN, iss=f"https://login.microsoftonline.com/{FOREIGN}/v2.0")}, id="foreign_tenant"),
        pytest.param({"id_token": id_token(iss=f"https://login.microsoftonline.com/{FOREIGN}/v2.0")}, id="foreign_issuer"),
        pytest.param({"id_token": id_token(idp=f"https://sts.windows.net/{FOREIGN}/")}, id="guest_from_other_tenant"),
        pytest.param({"id_token": id_token(aud="another-application")}, id="other_audience"),
        pytest.param({"id_token": id_token(oid="someone-else")}, id="other_object_id"),
        pytest.param({"id_token": id_token(exp=int(time.time()) - 5)}, id="expired"),
        pytest.param({"id_token": id_token(tid=None)}, id="no_tenant_claim"),
        pytest.param({"id_token": id_token(exp="later")}, id="malformed_expiry"),
        pytest.param({"id_token": "not-a-jwt"}, id="malformed_token"),
        pytest.param({"id_token": "a.bm90LWpzb24.c"}, id="payload_not_json"),
        pytest.param({"access_token": "only"}, id="no_id_token"),
        pytest.param(None, id="no_response"),
    ],
)
def test_token_from_anywhere_else_is_refused(tenant, response):
    with pytest.raises(PermissionDenied):
        verified_microsoft_tenant(response, CLIENT, SUBJECT)


@pytest.mark.parametrize("configured", ["", "common", "organizations", "consumers"])
def test_unspecific_configuration_refuses_every_token(settings, configured):
    settings.MICROSOFT_TENANT_ID = configured
    with pytest.raises(PermissionDenied):
        verified_microsoft_tenant({"id_token": id_token()}, CLIENT, SUBJECT)


def graph_login(request, uid=SUBJECT, email="tenant.check@lacopts.org"):
    app = SocialApp(provider="microsoft", client_id=CLIENT, secret="synthetic-secret")
    return SocialLogin(
        account=SocialAccount(provider="microsoft", uid=uid),
        provider=MicrosoftGraphProvider(request, app=app),
        email_addresses=[EmailAddress(email=email, verified=True, primary=True)],
    )


def test_adapter_marks_only_tenant_checked_logins(tenant, monkeypatch):
    request = RequestFactory().get("/accounts/microsoft/login/callback/")
    monkeypatch.setattr(MicrosoftGraphOAuth2Adapter, "complete_login", lambda self, req, app, token, **kw: graph_login(req))
    app = SocialApp(provider="microsoft", client_id=CLIENT)
    adapter = CouncilMicrosoftAdapter(request)

    login = adapter.complete_login(request, app, None, response={"id_token": id_token()})
    assert login.ctm_verified_tenant == TENANT

    foreign = id_token(tid=FOREIGN, iss=f"https://login.microsoftonline.com/{FOREIGN}/v2.0")
    with pytest.raises(PermissionDenied):
        adapter.complete_login(request, app, None, response={"id_token": foreign})


def test_microsoft_callback_route_uses_the_tenant_checking_adapter():
    match = resolve("/accounts/microsoft/login/callback/")
    assert match.func is auth.microsoft_callback


# Sign-in level (PostgreSQL CI): a matching @lacopts.org enrolled account is
# still refused without a tenant-checked token, and refusals are uniform.

def unchecked_callback(request):
    login = graph_login(request)
    login.user = AccountAdapter(request).new_user(request, login)
    login.state = {"process": "login"}
    return complete_social_login(request, login)


def checked_callback(request):
    login = graph_login(request)
    login.ctm_verified_tenant = TENANT
    login.user = AccountAdapter(request).new_user(request, login)
    login.state = {"process": "login"}
    return complete_social_login(request, login)


urlpatterns = [
    path("_test/unchecked-callback/", unchecked_callback),
    path("_test/checked-callback/", checked_callback),
    path("", include("ctm.urls")),
]


@pytest.fixture
def callback_settings(settings, tenant):
    settings.ROOT_URLCONF = __name__
    settings.SOCIALACCOUNT_PROVIDERS = {"microsoft": {"APP": {"client_id": CLIENT, "secret": "synthetic-secret"}}}
    return settings


def test_enrolled_lacopts_account_is_refused_without_a_tenant_checked_token(granted_roles, people, client, callback_settings):
    from tribunal.models import Account
    from tribunal.services.identity import enroll_council

    member = enroll_council(people["admin"], "tenant.check@lacopts.org", "Tenant", "Check", "member")
    with granted_roles("ctm_app", session=True):
        response = client.get("/_test/unchecked-callback/")
    assert response.status_code == 403
    assert "_auth_user_id" not in client.session
    assert Account.objects.get(pk=member.pk).microsoft_subject == ""
    assert not SocialAccount.objects.exists()


def test_refused_first_binding_is_a_uniform_denial_not_a_server_error(granted_roles, people, client, callback_settings):
    from django.db import connection
    from tribunal.models import Account

    # Matching active @lacopts.org council email, but never enrolled by an
    # administrator: the database function refuses the binding.
    stranger = Account.objects.create_user(
        email="tenant.check@lacopts.org", role="member", first_name="Not", last_name="Enrolled"
    )
    with granted_roles("ctm_app", session=True):
        response = client.get("/_test/checked-callback/")
        assert response.status_code == 403
        assert b"admin" not in response.content.lower()
        with connection.cursor() as cursor:  # the transaction is still usable
            cursor.execute("SELECT 1")
            assert cursor.fetchone() == (1,)
    assert "_auth_user_id" not in client.session
    assert Account.objects.get(pk=stranger.pk).microsoft_subject == ""


def test_refusal_log_names_only_the_failed_checks(tenant, caplog):
    guest = id_token(idp=f"https://sts.windows.net/{FOREIGN}/", aud="another-application")
    with caplog.at_level("WARNING", logger="tribunal.auth"), pytest.raises(PermissionDenied):
        verified_microsoft_tenant({"id_token": guest}, CLIENT, SUBJECT)
    message = caplog.records[-1].getMessage()
    assert message.endswith("(failed: idp,aud)")
    assert FOREIGN not in message and SUBJECT not in message


def test_refusal_log_names_an_unreadable_token(tenant, caplog):
    with caplog.at_level("WARNING", logger="tribunal.auth"), pytest.raises(PermissionDenied):
        verified_microsoft_tenant({"access_token": "only"}, CLIENT, SUBJECT)
    assert "unreadable-id-token:KeyError" in caplog.records[-1].getMessage()


def test_microsoft_scope_requests_profile_so_the_id_token_has_oid(monkeypatch):
    # Microsoft only puts the oid claim in a v2.0 id_token when the profile
    # scope is requested; without it the oid check refuses every sign-in.
    import importlib

    import ctm.settings as ctm_settings

    monkeypatch.setenv("MICROSOFT_CLIENT_ID", "client-for-scope-test")
    reloaded = importlib.reload(ctm_settings)
    try:
        scope = reloaded.SOCIALACCOUNT_PROVIDERS["microsoft"]["SCOPE"]
        assert {"openid", "profile", "User.Read"} <= set(scope)
    finally:
        monkeypatch.delenv("MICROSOFT_CLIENT_ID")
        importlib.reload(ctm_settings)
