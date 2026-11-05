from django.core.exceptions import PermissionDenied
from django.conf import settings
from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from .models import Account, Person
import json
import uuid
from contextlib import contextmanager
from tribunal.db.context import database_settings


@contextmanager
def provider_identity(sociallogin):
    provider = sociallogin.account.provider
    if provider not in {"microsoft", "google", "apple"}:
        raise PermissionDenied("Unsupported identity provider.")
    if provider == "microsoft" and (not settings.MICROSOFT_TENANT_ID or
            settings.MICROSOFT_TENANT_ID.lower() in {"common", "organizations", "consumers"}):
        raise PermissionDenied("A specific council tenant is required.")
    emails = [email.email.lower() for email in getattr(sociallogin, "email_addresses", []) if email.verified]
    with database_settings({"ctm.provider": provider, "ctm.provider_subject": str(sociallogin.account.uid),
                            "ctm.provider_emails": json.dumps(emails)}):
        yield


def bind_first_microsoft_subject(user, subject):
    """Record an enrolled council account's first Microsoft subject.

    On PostgreSQL the runtime role cannot change identity fields; the narrow
    ctm_bind_microsoft_subject function re-checks every condition (validated
    provider settings, active administrator-enrolled council account, empty
    subject, verified @lacopts.org email, unused subject) before binding.
    """
    from django.db import connection

    if connection.vendor == "postgresql":
        with connection.cursor() as cursor:
            cursor.execute("SELECT public.ctm_bind_microsoft_subject(%s)", [str(user.pk)])
        user.refresh_from_db(fields=["microsoft_subject"])
        return
    user.microsoft_subject = subject
    user.save(update_fields=["microsoft_subject"])


class ProviderOnlyAdapter(DefaultAccountAdapter):
    def is_open_for_signup(self, request):
        return False


class AccountAdapter(DefaultSocialAccountAdapter):
    def new_user(self, request, sociallogin):
        # allauth invokes lookup after its provider adapter has validated the
        # response. Scope that instance's lookup; never authorize by URL claims.
        lookup = sociallogin.lookup
        def scoped_lookup():
            with provider_identity(sociallogin):
                return lookup()
        sociallogin.lookup = scoped_lookup
        return super().new_user(request, sociallogin)

    def is_open_for_signup(self, request, sociallogin):
        return sociallogin.account.provider in {"google", "apple"}

    def pre_social_login(self, request, sociallogin):
        with provider_identity(sociallogin):
            result = self._pre_social_login(request, sociallogin)
        # allauth rechecks is_existing and completes login after this hook.
        # Extend only a successfully validated identity to the response boundary.
        scope = getattr(request, "_ctm_provider_scope", None)
        if scope is not None:
            scope.enter_context(provider_identity(sociallogin))
        return result

    def _pre_social_login(self, request, sociallogin):
        provider = sociallogin.account.provider
        if provider == "microsoft":
            tenant = settings.MICROSOFT_TENANT_ID
            if not tenant or tenant.lower() in {"common", "organizations", "consumers"}:
                raise PermissionDenied(
                    "Configure the specific council Microsoft tenant before enabling login."
                )
            verified = [
                email.email.lower()
                for email in sociallogin.email_addresses
                if email.verified
            ]
            if sociallogin.is_existing:
                user = sociallogin.user
            else:
                # A previously bound Microsoft object is always authoritative.
                # For an enrolled council account without a binding, allow exactly
                # one first sign-in only when Microsoft has verified that account's
                # pre-existing, active council email.  This supports the approved
                # lacopts.org roster without granting access by domain alone.
                user = Account.objects.filter(
                    microsoft_subject=sociallogin.account.uid
                ).first()
                if user is None:
                    user = (
                        Account.objects.filter(
                            email__in=verified,
                            email__iendswith="@lacopts.org",
                            is_active=True,
                            microsoft_subject="",
                        )
                        .exclude(role="applicant")
                        .first()
                    )
                    if user is not None:
                        bind_first_microsoft_subject(user, sociallogin.account.uid)
            if (
                not user
                or not user.is_active
                or user.role == "applicant"
                or not user.microsoft_subject
                or user.microsoft_subject != sociallogin.account.uid
            ):
                raise PermissionDenied(
                    "Council Microsoft identity must match an active enrolled council email."
                )
            if not sociallogin.is_existing:
                sociallogin.connect(request, user)
            if not user.email_verified:
                user.email_verified = True
                user.save(update_fields=["email_verified"])
            return
        if sociallogin.is_existing:
            user = sociallogin.user
            if not user.is_active or (
                user.role != "applicant" and provider != "microsoft"
            ):
                raise PermissionDenied("Account/provider not authorized.")
            return
        verified = [
            email.email.lower()
            for email in sociallogin.email_addresses
            if email.verified
        ]
        if not verified:
            raise PermissionDenied("A provider-verified email address is required.")
        if Account.objects.filter(email__in=verified).exists():
            raise PermissionDenied(
                "Sign in through your existing provider to link another identity."
            )

    def save_user(self, request, sociallogin, form=None):
        user = sociallogin.user
        user.role = "applicant"
        user.email_verified = any(x.verified for x in sociallogin.email_addresses)
        person_id = uuid.uuid4()
        with provider_identity(sociallogin), database_settings({"ctm.registration_account": str(user.pk),
                "ctm.registration_person": str(person_id), "ctm.registration_email": user.email.lower()}):
            user.person = Person.objects.create(id=person_id, first_name=user.first_name, last_name=user.last_name)
            user.set_unusable_password()
            return super().save_user(request, sociallogin, form)
