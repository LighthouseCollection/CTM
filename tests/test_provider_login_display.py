import pytest
from django.template.loader import render_to_string
from tribunal.models import Account


@pytest.mark.django_db
def test_provider_login_success_message_supports_email_only_account():
    user = Account.objects.create_user(email="provider-review@example.test", role="admin")
    # allauth renders this during post_login, after the provider identity links.
    message = render_to_string("account/messages/logged_in.txt", {"user": user})
    assert message.strip()
