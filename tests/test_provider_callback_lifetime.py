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
from tribunal.services.identity import enroll_council
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


def email_bootstrap_callback(request):
    app = SocialApp(provider="microsoft", client_id="synthetic-client", secret="synthetic-secret")
    login = SocialLogin(
        user=Account(email="admin@lacopts.org", first_name="Admin", last_name="User"),
        account=SocialAccount(provider="microsoft", uid="email-bootstrap-subject"),
        provider=MicrosoftGraphProvider(request, app=app),
        email_addresses=[EmailAddress(email="admin@lacopts.org", verified=True, primary=True)],
    )
    login.user = AccountAdapter(request).new_user(request, login)
    login.state = {"process": "login"}
    return complete_social_login(request, login)


urlpatterns = [
    path("_test/validated-callback/", validated_callback),
    path("_test/email-bootstrap-callback/", email_bootstrap_callback),
    path("", include("ctm.urls")),
]


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


def test_verified_enrolled_council_email_binds_microsoft_identity_on_first_login(granted_roles, people, client, settings):
    settings.ROOT_URLCONF = __name__
    settings.MICROSOFT_TENANT_ID = "specific-synthetic-tenant"
    settings.SOCIALACCOUNT_PROVIDERS = {"microsoft": {"APP": {"client_id": "synthetic-client", "secret": "synthetic-secret"}}}
    # The binding path accepts only an administrator-enrolled council account.
    admin = enroll_council(people["admin"], "admin@lacopts.org", "Admin", "User", "member")
    assert admin.microsoft_subject == "" and not admin.email_verified

    with granted_roles("ctm_app", session=True):
        response = client.get("/_test/email-bootstrap-callback/")
        assert response.status_code == 302, response.content
        assert client.session["_auth_user_id"] == str(admin.pk)
    admin.refresh_from_db()
    assert admin.microsoft_subject == "email-bootstrap-subject"
    assert admin.email_verified
    assert SocialAccount.objects.filter(user=admin, provider="microsoft", uid="email-bootstrap-subject").count() == 1


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


BINDING_REFUSALS = ["not_microsoft", "empty_subject", "unverified_email", "other_domain", "inactive", "applicant",
                    "already_bound", "subject_in_use", "not_admin_enrolled"]


@pytest.mark.parametrize("refusal", BINDING_REFUSALS)
def test_first_microsoft_binding_refuses_every_unqualified_account(granted_roles, people, refusal):
    import json
    from django.db import DatabaseError
    from tribunal.db.context import database_settings

    email = "other@example.test" if refusal == "other_domain" else "first.binding@lacopts.org"
    if refusal == "not_admin_enrolled":
        account = Account.objects.create_user(email=email, role="member", first_name="First", last_name="Binding")
    elif refusal == "applicant":
        account = Account.objects.create_user(email=email, role="applicant", first_name="First", last_name="Binding")
    else:
        account = enroll_council(people["admin"], email, "First", "Binding", "member",
                                 "existing-subject" if refusal == "already_bound" else None)
    if refusal == "inactive":
        account.is_active = False
        account.save(update_fields=["is_active"])
    if refusal == "subject_in_use":
        holder = people["member"]
        holder.microsoft_subject = "first-binding-subject"
        holder.save(update_fields=["microsoft_subject"])
    values = {
        "ctm.provider": "google" if refusal == "not_microsoft" else "microsoft",
        "ctm.provider_subject": "" if refusal == "empty_subject" else "first-binding-subject",
        "ctm.provider_emails": json.dumps([] if refusal == "unverified_email" else [email]),
    }
    with pytest.raises(DatabaseError):
        with granted_roles("ctm_app", session=True), database_settings(values), connection.cursor() as cursor:
            cursor.execute("SELECT public.ctm_bind_microsoft_subject(%s)", [str(account.pk)])
    account.refresh_from_db()
    assert account.microsoft_subject == ("existing-subject" if refusal == "already_bound" else "")


def test_runtime_role_cannot_bind_a_subject_outside_the_binding_function(granted_roles, people):
    import json
    from django.db import DatabaseError
    from tribunal.db.context import database_settings

    account = enroll_council(people["admin"], "direct.binding@lacopts.org", "Direct", "Binding", "member")
    values = {"ctm.provider": "microsoft", "ctm.provider_subject": "direct-subject",
              "ctm.provider_emails": json.dumps(["direct.binding@lacopts.org"])}
    # A direct identity write is refused by ctm_core_guard.
    with pytest.raises(DatabaseError):
        with granted_roles("ctm_app", session=True), database_settings(values), connection.cursor() as cursor:
            cursor.execute("UPDATE public.tribunal_account SET microsoft_subject='direct-subject' WHERE id=%s", [str(account.pk)])
    # The guard's grant row cannot be forged by the runtime role.
    with pytest.raises(DatabaseError):
        with granted_roles("ctm_app", session=True), database_settings(values), connection.cursor() as cursor:
            cursor.execute("INSERT INTO public.ctm_microsoft_binding_grant(account_id,subject) VALUES (%s,'direct-subject')", [str(account.pk)])
    # Once bound, the function cannot change the subject, and only an empty subject is ever replaced.
    with granted_roles("ctm_app", session=True), database_settings(values), connection.cursor() as cursor:
        cursor.execute("SELECT public.ctm_bind_microsoft_subject(%s)", [str(account.pk)])
    account.refresh_from_db()
    assert account.microsoft_subject == "direct-subject"
    rebind = {**values, "ctm.provider_subject": "second-subject"}
    with pytest.raises(DatabaseError):
        with granted_roles("ctm_app", session=True), database_settings(rebind), connection.cursor() as cursor:
            cursor.execute("SELECT public.ctm_bind_microsoft_subject(%s)", [str(account.pk)])
    account.refresh_from_db()
    assert account.microsoft_subject == "direct-subject"
    with connection.cursor() as cursor:
        cursor.execute("SELECT count(*) FROM public.ctm_microsoft_binding_grant")
        assert cursor.fetchone()[0] == 0


def test_binding_function_is_executable_only_by_the_app_role(granted_roles):
    with connection.cursor() as cursor:
        cursor.execute("""SELECT coalesce(r.rolname, 'PUBLIC') FROM pg_proc p,
            LATERAL aclexplode(coalesce(p.proacl, acldefault('f', p.proowner))) access
            LEFT JOIN pg_roles r ON r.oid = access.grantee
            WHERE p.oid = 'public.ctm_bind_microsoft_subject(uuid)'::regprocedure
              AND access.privilege_type = 'EXECUTE' AND access.grantee <> p.proowner""")
        assert [row[0] for row in cursor.fetchall()] == ["ctm_app"]
        cursor.execute("""SELECT count(*) FROM aclexplode(coalesce((SELECT relacl FROM pg_class
            WHERE oid = 'public.ctm_microsoft_binding_grant'::regclass), '{}'::aclitem[])) access
            WHERE access.grantee <> (SELECT relowner FROM pg_class WHERE oid = 'public.ctm_microsoft_binding_grant'::regclass)""")
        assert cursor.fetchone()[0] == 0
