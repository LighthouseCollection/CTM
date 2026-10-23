from tribunal.db.context import core_operation
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
from django.core.validators import validate_email
from tribunal.db.context import database_actor
from .common import audit, lock_key, notify
import uuid
from tribunal.db.context import database_settings


@transaction.atomic
@core_operation("preferences")
def save_preferences(actor, values):
    active(actor)
    allowed = {"ui_language", "notification_language", "first_name", "last_name"}
    if not values or set(values) - allowed:
        raise ValidationError("Choose supported account settings only.")
    languages = {"ui_language", "notification_language"}
    if any(not isinstance(values[key], str) or values[key] not in {"en", "ar"} for key in languages & values.keys()):
        raise ValidationError("Choose English or Arabic for the supported language preferences.")
    names = {"first_name", "last_name"}
    if any(not isinstance(values[key], str) or not values[key].strip() or len(values[key].strip()) > 150 for key in names & values.keys()):
        raise ValidationError("Enter a first and last name up to 150 characters.")
    user = Account.objects.select_for_update().select_related("person").get(pk=actor.pk)
    active(user)
    changed = []
    before = {}
    for field, value in values.items():
        value = value.strip() if field in names else value
        if getattr(user, field) != value:
            before[field] = getattr(user, field)
            setattr(user, field, value)
            changed.append(field)
    if changed:
        user.save(update_fields=changed)
        if user.person and names & set(changed):
            person_changes = [field for field in names & set(changed) if getattr(user.person, field) != getattr(user, field)]
            for field in person_changes:
                setattr(user.person, field, getattr(user, field))
            if person_changes:
                user.person.save(update_fields=person_changes)
        action = "account_profile_changed" if names & set(changed) else "account_preferences_changed"
        audit(actor, action, user, metadata={"before": before, "after": {field: getattr(user, field) for field in changed}})
    return user


@transaction.atomic
def enroll_council(
    actor, email, first_name, last_name, role="member", microsoft_subject=None
):
    active(actor)
    if actor.role != "admin":
        raise PermissionDenied("Only an existing admin can create council membership.")
    if role not in {"member", "president", "secretary", "admin"}:
        raise ValidationError("Invalid council role.")
    if not isinstance(email, str) or len(email)>254:
        raise ValidationError("A valid council email is required.")
    email = email.strip().lower()
    validate_email(email)
    if any(not isinstance(value, str) or len(value)>150 for value in [first_name, last_name]):
        raise ValidationError("Council names must be text up to150 characters.")
    if microsoft_subject is not None and (not isinstance(microsoft_subject, str) or len(microsoft_subject)>200):
        raise ValidationError("Invalid preauthorized Microsoft subject.")
    user_id, person_id = uuid.uuid4(), uuid.uuid4()
    with database_settings({"ctm.enroll_account": str(user_id), "ctm.enroll_person": str(person_id)}):
        person = Person.objects.create(id=person_id, first_name=first_name, last_name=last_name)
        user = Account.objects.create_user(id=user_id, person=person, email=email,
            first_name=first_name, last_name=last_name, role=role, microsoft_subject=microsoft_subject or "")
    audit(actor, "council_enrolled", user)
    return user


@transaction.atomic
@core_operation("account_status")
def set_account_status(actor, target_id, enabled, *, expected_version=None):
    from tribunal.validation import VersionConflict
    from .account_administration import status_version, notice_template, queue_status_notice
    administrator(actor)
    if type(enabled) is not bool:
        raise ValidationError("Account enabled must be a literal boolean.")
    if expected_version is not None and (type(expected_version) is not int or expected_version<0):
        raise ValidationError("expected_version must be a non-negative status version.")
    with database_actor(actor):
        lock_key("account-administration")
        # Match the setting writer's lock order before taking recipient FK locks.
        lock_key("setting:email_templates")
        target = Account.objects.select_for_update(of=("self",)).get(pk=target_id)
        version=status_version(target.pk)
        if expected_version is not None and expected_version!=version:
            raise VersionConflict(version)
        if target.pk == actor.pk and not enabled:
            raise ValidationError("Cannot suspend your own administrator session.")
        if target.role == "admin" and not enabled and not Account.objects.filter(role="admin", is_active=True).exclude(pk=target.pk).exists():
            raise ValidationError("The last active administrator cannot be suspended.")
        changed=target.is_active!=enabled
        action="account_reactivated" if enabled else "account_suspended"
        template=notice_template(target,action) if changed and target.role=='applicant' else None
        before=target.is_active
        if changed:
            target.is_active=enabled
            target.save(update_fields=["is_active"])
        revoked=0
        if not enabled:
            from django.contrib.sessions.models import Session
            from django.utils import timezone
            for session in Session.objects.filter(expire_date__gte=timezone.now()).iterator():
                if session.get_decoded().get("_auth_user_id") == str(target.pk):
                    session.delete()
                    revoked+=1
        target.revoked_sessions=revoked
        target.notice_queued=False
        if not changed and revoked:
            audit(actor,"account_sessions_revoked",target,metadata={'sessions_revoked':revoked})
        if changed:
            event=audit(actor,action,target,metadata={'before':before,'after':enabled,
                'status_version':version+1,'sessions_revoked':revoked,
                'notification_language':target.notification_language,
                'template_version':template['template_version'] if template else None})
            if template:
                queue_status_notice(target,event,template)
                target.notice_queued=True
        return target


@transaction.atomic
def link_party(actor, case, account):
    administrator(actor)
    return link_authorized_party(actor, case, account)


@core_operation("onboarding")
def link_authorized_party(actor, case, account):
    """Internal continuation of an already-authorized pending association."""
    administrator(actor)
    if account.role != "applicant" or not account.person_id or not account.email_verified or not account.is_active:
        raise ValidationError("Linking requires an active verified account.")
    lock_key(f"person:{account.person_id}")
    case = Case.objects.select_for_update(of=("self",)).get(pk=case.pk)
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
    if not isinstance(email, str) or len(email)>254:
        raise ValidationError("A valid applicant email is required.")
    email = email.strip().lower()
    validate_email(email)
    if any(not isinstance(value, str) or not value.strip() or len(value)>150 for value in [first_name, last_name]):
        raise ValidationError("Applicant names must be nonempty text up to150 characters.")
    account = Account.objects.filter(email=email, email_verified=True, is_active=True, role="applicant").first()
    if account:
        lock_key(f"person:{account.person_id}")
    case = Case.objects.select_for_update(of=("self",)).get(pk=case_id)
    existing = PendingPartyLink.objects.filter(case=case, email=email, state="pending").first()
    if existing:
        if (existing.first_name, existing.last_name) != (first_name, last_name):
            raise ValidationError("Pending association already has different recorded names; review it before replacement.")
        if account:
            activate_pending_links(account)
            existing.refresh_from_db()
        return existing
    pending = PendingPartyLink.objects.create(
        case=case,
        actor=actor,
        first_name=first_name,
        last_name=last_name,
        email=email,
    )
    account = Account.objects.filter(
        email=pending.email, email_verified=True, is_active=True, role="applicant"
    ).first()
    if account:
        activate_pending_links(account)
    audit(actor, "pending_party_added", pending, case)
    return pending


@transaction.atomic
@core_operation("activation", target_arg=0)
def activate_pending_links(account):
    if (
        not account.email_verified
        or not account.is_active
        or account.role != "applicant"
    ):
        return []
    result = []
    lock_key(f"person:{account.person_id}")
    for candidate in (
        PendingPartyLink.objects
        .filter(email=account.email.lower(), state="pending")
        .order_by("case_id", "id")
    ):
        Case.objects.select_for_update(of=("self",)).get(pk=candidate.case_id)
        pending = PendingPartyLink.objects.select_for_update(of=("self",)).select_related("case", "actor").get(pk=candidate.pk)
        if pending.state != "pending":
            continue
        if not pending.actor.is_active or pending.actor.role not in {"admin", "secretary"}:
            pending.state = "needs_review"
            pending.save(update_fields=["state"])
            with database_actor(account):
                audit(account, "party_link_authority_review", pending, pending.case)
            continue
        # Reuse the recorded authorized actor; registration never confers staff authority.
        with database_actor(pending.actor):
            party = link_authorized_party(pending.actor, pending.case, account)
        pending.activated_party = party
        pending.state = "activated"
        pending.save(update_fields=["activated_party", "state"])
        with database_actor(account):
            audit(account, "verified_party_link_activated", pending, pending.case,
                metadata={"authorized_actor_id": str(pending.actor_id)})
        result.append(party)
    return result


@transaction.atomic
def cancel_pending_link(actor, pending_id):
    administrator(actor)
    row = PendingPartyLink.objects.select_for_update(of=("self",)).get(pk=pending_id)
    if row.state == "cancelled":
        return row
    if row.state not in {"pending", "needs_review"} or row.activated_party_id:
        raise ValidationError("An activated association requires a separate identity correction.")
    row.state = "cancelled"
    row.save(update_fields=["state"])
    audit(actor, "pending_party_cancelled", row, row.case)
    return row
