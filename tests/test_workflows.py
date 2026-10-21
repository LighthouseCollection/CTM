"""Business acceptance tests; real ORM and commands, never mocked authorization."""

from datetime import date
import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.utils import timezone

pytestmark = pytest.mark.django_db


def test_provider_only_account_has_no_usable_password():
    from tribunal.models import Account

    user = Account.objects.create_user(
        email="a@example.test", first_name="John", last_name="Smith"
    )
    assert not user.has_usable_password()


def test_only_existing_admin_can_enroll_council():
    from tribunal.models import Account
    from tribunal.services.identity import enroll_council

    secretary = Account.objects.create_user(
        email="secretary@example.test", role="secretary", email_verified=True
    )
    with pytest.raises(PermissionDenied):
        enroll_council(secretary, "member@example.test", "M", "A", "member")


def test_one_draft_and_no_council_draft_visibility():
    from tribunal.services.applications import start_application
    from tribunal.policy import visible_applications
    from tribunal.models import Account

    user = Account.objects.create_user(email="a@example.test", email_verified=True)
    member = Account.objects.create_user(
        email="m@example.test", role="member", email_verified=True
    )
    first = start_application(user)
    assert start_application(user).pk == first.pk
    assert list(visible_applications(member)) == []


def test_submission_requires_verified_account_and_fee_and_documents():
    from tribunal.models import Account
    from tribunal.services.applications import start_application, submit_application

    user = Account.objects.create_user(email="a@example.test")
    draft = start_application(user)
    with pytest.raises(ValidationError):
        submit_application(user, draft.pk, "one")


def test_closed_proceeding_is_not_unlocked_by_appeal():
    from tribunal.models import Case, Proceeding

    case = Case.objects.create(number="20261021-01", status="closed")
    original = Proceeding.objects.create(
        case=case, kind="initial", status="closed", closed_at=timezone.now()
    )
    Proceeding.objects.create(case=case, kind="appeal", status="open", sequence=1)
    original.refresh_from_db()
    assert original.status == "closed"


def test_answer_history_is_immutable():
    from tribunal.models import Account, Application, AnswerRevision

    user = Account.objects.create_user(email="a@example.test")
    app = Application.objects.create(owner=user)
    rev = AnswerRevision.objects.create(
        application=app, number=1, answers={"name": "Original"}, actor=user
    )
    rev.answers = {"name": "Changed"}
    with pytest.raises(ValidationError):
        rev.save()


def test_applicant_cannot_read_other_application():
    from tribunal.models import Account
    from tribunal.services.applications import start_application
    from tribunal.policy import application_for

    a = Account.objects.create_user(email="a@example.test")
    b = Account.objects.create_user(email="b@example.test")
    draft = start_application(a)
    with pytest.raises(PermissionDenied):
        application_for(b, draft.pk)


def test_case_number_uses_los_angeles_date():
    from datetime import datetime, timezone as tz
    from tribunal.services.applications import allocate_case_number

    assert (
        allocate_case_number(datetime(2026, 10, 22, 1, 0, tzinfo=tz.utc))
        == "20261021-01"
    )
    assert (
        allocate_case_number(datetime(2026, 10, 22, 1, 1, tzinfo=tz.utc))
        == "20261021-02"
    )
