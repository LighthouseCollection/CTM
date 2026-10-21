import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from tribunal.models import (
    Account,
    OpenCaseClaim,
    HistoricalWorkspace,
    PendingPartyLink,
    Party,
    Case,
)
from tribunal.services.applications import submit_application

pytestmark = pytest.mark.django_db


def test_historical_entry_preserves_number_and_missing_documents(people):
    from tribunal.services.historical import stage, publish

    workspace = stage(
        people["admin"],
        {
            "number": "LA-1990-123",
            "status": "closed",
            "parties": [
                {"slot": "A", "name": "Known name", "legacy_reference": "OLD123"}
            ],
        },
    )
    assert workspace.finalized_case_id is None
    case = publish(people["admin"], workspace.pk)
    assert case.number == "LA-1990-123" and case.status == "closed"
    assert case.parties.get().reference == "OLD123"


def test_historical_open_case_enforces_existing_claim(ready_application, people):
    from tribunal.services.historical import stage, publish

    app = ready_application
    submit_application(
        app.owner, app.pk, "hist", {"accepted": True, "name": "John Smith"}
    )
    workspace = stage(
        people["admin"],
        {
            "number": "OLDER",
            "status": "open",
            "parties": [
                {"slot": "A", "name": "John Smith", "account_id": str(app.owner_id)}
            ],
        },
    )
    with pytest.raises(ValidationError):
        publish(people["admin"], workspace.pk)
    assert not Case.objects.filter(number="OLDER").exists()


def test_pending_party_requires_matching_verified_account(ready_application, people):
    from tribunal.services.identity import add_other_party, activate_pending_links

    app = ready_application
    submit_application(
        app.owner, app.pk, "link", {"accepted": True, "name": "John Smith"}
    )
    app.refresh_from_db()
    pending = add_other_party(
        people["secretary"], app.case_id, "Jane", "Smith", "jane@example.test"
    )
    user = Account.objects.create_user(email="jane@example.test")
    assert activate_pending_links(user) == []
    user.email_verified = True
    user.save(update_fields=["email_verified"])
    result = activate_pending_links(user)
    assert len(result) == 1
    assert Party.objects.filter(case=app.case, account=user).exists()


def test_manual_calls_store_actual_time_separately(ready_application, people):
    from tribunal.services.communications import log_call
    from django.utils import timezone

    app = ready_application
    submit_application(
        app.owner, app.pk, "call", {"accepted": True, "name": "John Smith"}
    )
    app.refresh_from_db()
    occurred = timezone.now() - timezone.timedelta(days=2)
    record = log_call(
        people["admin"], app.case_id, app.party_id, occurred, "Spoke", "Notes"
    )
    assert record.occurred_at == occurred and record.created_at > occurred


def test_admin_can_enroll_without_configured_subject(people):
    from tribunal.services.identity import enroll_council

    user = enroll_council(people["admin"], "new-member@example.test", "New", "Member")
    assert user.microsoft_subject == "" and not user.has_usable_password()


def test_link_closed_history_does_not_conflict_with_current_case(
    ready_application, people
):
    from tribunal.services.identity import link_party

    app = ready_application
    submit_application(
        app.owner, app.pk, "historical-link", {"accepted": True, "name": "John Smith"}
    )
    old = Case.objects.create(number="OLD-CLOSED", status="closed", origin="historical")
    party = link_party(people["secretary"], old, app.owner)
    assert party.account_id == app.owner_id
    assert OpenCaseClaim.objects.get(person=app.owner.person).case_id != old.pk
