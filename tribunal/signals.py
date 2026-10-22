from django.dispatch import receiver
from django.db import IntegrityError
from django.core.exceptions import ValidationError
from allauth.account.signals import user_logged_in
from tribunal.db.context import database_actor
from django.contrib.auth.signals import user_logged_in as django_user_logged_in
from django.contrib.auth.models import update_last_login


def scoped_last_login(sender, user, **kwargs):
    with database_actor(user):
        update_last_login(sender, user, **kwargs)


django_user_logged_in.disconnect(update_last_login, dispatch_uid="update_last_login")
django_user_logged_in.connect(scoped_last_login, dispatch_uid="ctm_scoped_last_login")


@receiver(user_logged_in)
def activate_verified_case_links(sender, request, user, **kwargs):
    from tribunal.services.identity import activate_pending_links

    if user.role != "applicant" or not user.email_verified:
        return
    try:
        with database_actor(user):
            activate_pending_links(user)
    except (ValidationError, IntegrityError):
        # The atomic activation rolled back: leave its pending association intact.
        # An applicant cannot turn a conflict into staff review authority. Keep login
        # available and let the authorized issuer review/cancel the pending record.
        import logging
        logging.getLogger(__name__).warning("Pending party activation requires authorized review")
