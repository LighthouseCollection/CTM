from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from tribunal.models import (
    Account,
    Party,
    OpenCaseClaim,
    Person,
    PendingPartyLink,
    Case,
)
from tribunal.policy import active, administrator
from .common import audit, lock_key, notify


@transaction.atomic
def enroll_council(
    actor, email, first_name, last_name, role="member", microsoft_subject=None
):
    active(actor)
    if actor.role != "admin":
        raise PermissionDenied("Only an existing admin can create council membership.")
    if role not in {"member", "president", "secretary", "admin"}:
        raise ValidationError("Invalid council role.")
    user = Account.objects.create_user(
        email=email,
        first_name=first_name,
        last_name=last_name,
        role=role,
        microsoft_subject=microsoft_subject or "",
    )
    audit(actor, "council_enrolled", user)
    return user


@transaction.atomic
def set_account_status(actor, target_id, enabled):
    administrator(actor)
    target = Account.objects.select_for_update(of=("self",)).get(pk=target_id)
    if target.pk == actor.pk and not enabled:
        raise ValidationError("Cannot suspend your own administrator session.")
    target.is_active = bool(enabled)
    target.save(update_fields=["is_active"])
    if not enabled:
        from django.contrib.sessions.models import Session

        for session in Session.objects.filter(
            expire_date__gte=__import__("django").utils.timezone.now()
        ):
            if session.get_decoded().get("_auth_user_id") == str(target.pk):
                session.delete()
    audit(actor, "account_reactivated" if enabled else "account_suspended", target)
    return target


@transaction.atomic
def link_party(actor, case, account):
    administrator(actor)
    return link_authorized_party(actor, case, account)


def link_authorized_party(actor, case, account):
    """Internal continuation of an already-authorized pending association."""
    if not account.email_verified or not account.is_active:
        raise ValidationError("Linking requires an active verified account.")
    lock_key(f"person:{account.person_id}")
    claim = OpenCaseClaim.objects.filter(person=account.person).first()
    if case.status == "open" and claim and claim.case_id != case.pk:
        raise ValidationError("Applicant already has another open case.")
    party = case.parties.filter(account=account).first()
    if party:
        return party
    used = set(case.parties.values_list("slot", flat=True))
    slot = next((x for x in ["A", "B"] if x not in used), None)
    if slot is None:
        raise ValidationError(
            "Both case parties already exist; association review required."
        )
    party = Party.objects.create(
        case=case,
        account=account,
        person=account.person,
        slot=slot,
        name=f"{account.first_name} {account.last_name}".strip(),
    )
    if case.status == "open":
        OpenCaseClaim.objects.get_or_create(
            person=account.person, defaults={"case": case}
        )
    audit(actor, "party_linked", party, case)
    return party


@transaction.atomic
def add_other_party(actor, case_id, first_name, last_name, email):
    administrator(actor)
    case = Case.objects.select_for_update(of=("self",)).get(pk=case_id)
    pending = PendingPartyLink.objects.create(
        case=case,
        actor=actor,
        first_name=first_name,
        last_name=last_name,
        email=email.strip().lower(),
    )
    account = Account.objects.filter(
        email=pending.email, email_verified=True, is_active=True, role="applicant"
    ).first()
    if account:
        activate_pending_links(account)
    audit(actor, "pending_party_added", pending, case)
    return pending


@transaction.atomic
def activate_pending_links(account):
    if (
        not account.email_verified
        or not account.is_active
        or account.role != "applicant"
    ):
        return []
    result = []
    lock_key(f"person:{account.person_id}")
    for pending in (
        PendingPartyLink.objects.select_for_update(of=("self",))
        .filter(email=account.email.lower(), state="pending")
        .select_related("case")
    ):
        # Reuse the recorded authorized actor; registration never confers staff authority.
        party = link_authorized_party(pending.actor, pending.case, account)
        pending.activated_party = party
        pending.state = "activated"
        pending.save(update_fields=["activated_party", "state"])
        audit(None, "verified_party_link_activated", pending, pending.case)
        result.append(party)
    return result
