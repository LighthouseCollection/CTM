from django.dispatch import receiver
from django.db import IntegrityError
from django.core.exceptions import ValidationError
from allauth.account.signals import user_logged_in
from tribunal.models import PendingPartyLink


@receiver(user_logged_in)
def activate_verified_case_links(sender, request, user, **kwargs):
    from tribunal.services.identity import activate_pending_links

    if user.role != "applicant" or not user.email_verified:
        return
    try:
        activate_pending_links(user)
    except (ValidationError, IntegrityError):
        # A registration may expose a one-open-case conflict. Keep login working,
        # with the link explicitly withheld for authorized association review.
        PendingPartyLink.objects.filter(
            email=user.email.lower(), state="pending"
        ).update(state="review")
