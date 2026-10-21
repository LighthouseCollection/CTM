from django.core.exceptions import PermissionDenied
from django.conf import settings
from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from .models import Account, Person


class ProviderOnlyAdapter(DefaultAccountAdapter):
    def is_open_for_signup(self, request):
        return False


class AccountAdapter(DefaultSocialAccountAdapter):
    def is_open_for_signup(self, request, sociallogin):
        return sociallogin.account.provider in {"google", "apple"}

    def pre_social_login(self, request, sociallogin):
        provider = sociallogin.account.provider
        if provider == "microsoft":
            tenant = settings.MICROSOFT_TENANT_ID
            if not tenant or tenant.lower() in {"common", "organizations", "consumers"}:
                raise PermissionDenied(
                    "Configure the specific council Microsoft tenant before enabling login."
                )
            if sociallogin.is_existing:
                user = sociallogin.user
            else:
                user = (
                    Account.objects.filter(
                        microsoft_subject=sociallogin.account.uid, is_active=True
                    )
                    .exclude(role="applicant")
                    .first()
                )
            if (
                not user
                or not user.is_active
                or user.role == "applicant"
                or not user.microsoft_subject
                or user.microsoft_subject != sociallogin.account.uid
            ):
                raise PermissionDenied(
                    "Council Microsoft object identity must be preauthorized by admin."
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
        user.person = Person.objects.create(
            first_name=user.first_name, last_name=user.last_name
        )
        user.set_unusable_password()
        return super().save_user(request, sociallogin, form)
