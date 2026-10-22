"""F15 assignment authority adapter; does not expand decree/approval permissions."""
import uuid
from functools import wraps
from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from tribunal.models import Account, Tribunal, StaffMembership, StaffRole
from tribunal.policy import active
from .common import audit, lock_key
from tribunal.db.context import database_actor


def current_context(function):
    @wraps(function)
    def call(actor, *args, **kwargs):
        with database_actor(actor):
            return function(actor, *args, **kwargs)
    return call


def current_tribunal_id():
    try:
        return uuid.UUID(str(settings.CTM_TRIBUNAL_ID))
    except (ValueError, TypeError, AttributeError):
        return None


def assignment_authority(account, roles):
    if not account.is_active or account.role == "applicant":
        return False
    if account.role in roles:
        return True
    tribunal_id = current_tribunal_id()
    if not tribunal_id:
        return False
    now = timezone.now()
    return StaffRole.objects.filter(membership__account=account, membership__tribunal_id=tribunal_id,
        membership__account__is_active=True, membership__active_from__lte=now, role__in=roles, revoked_at__isnull=True).filter(
            Q(membership__active_until__isnull=True) | Q(membership__active_until__gt=now)).exists()


def assignment_president(account):
    return assignment_authority(account, {"president"})


def assignment_recorder(account):
    return assignment_authority(account, {"admin", "secretary"})


def existing_admin(actor):
    active(actor)
    if actor.role != "admin":
        raise PermissionDenied("An existing administrator must authorize council role grants.")


@transaction.atomic
@current_context
def create_tribunal(actor, code, name_en, name_ar=None):
    existing_admin(actor)
    if not isinstance(code, str) or not code.strip() or len(code) > 80 or not isinstance(name_en, str) or not name_en.strip() or len(name_en) > 250:
        raise ValidationError("Provide the institution's code and English name.")
    if name_ar is not None and (not isinstance(name_ar, str) or len(name_ar) > 250):
        raise ValidationError("Invalid Arabic institution name.")
    tribunal = Tribunal.objects.create(code=code.strip(), name_en=name_en.strip(), name_ar=name_ar)
    audit(actor, "tribunal_created", tribunal)
    return tribunal


@transaction.atomic
@current_context
def grant_assignment_authority(actor, account_id, tribunal_id, role="president"):
    existing_admin(actor)
    if role not in {"president", "admin", "secretary"}:
        raise ValidationError("Choose a supported assignment authority.")
    configured = current_tribunal_id()
    if not configured or str(configured) != str(tribunal_id):
        raise ValidationError("The explicitly configured current tribunal is required.")
    tribunal = Tribunal.objects.get(pk=configured)
    target = Account.objects.select_for_update(of=("self",)).get(pk=account_id, is_active=True)
    if target.role == "applicant":
        raise PermissionDenied("Only an existing council account may receive assignment authority.")
    lock_key(f"staff-role:{target.pk}:{tribunal.pk}")
    now = timezone.now()
    membership = StaffMembership.objects.filter(account=target, tribunal=tribunal, active_from__lte=now).filter(
        Q(active_until__isnull=True) | Q(active_until__gt=now)).order_by("-active_from", "-id").first()
    if membership is None:
        membership = StaffMembership.objects.create(account=target, tribunal=tribunal, appointed_by=actor)
        audit(actor, "staff_membership_created", membership)
    grant = StaffRole.objects.filter(membership=membership, role=role, revoked_at__isnull=True).first()
    if grant is None:
        grant = StaffRole.objects.create(membership=membership, role=role, granted_by=actor)
        audit(actor, "assignment_authority_granted", grant)
    return grant


@transaction.atomic
@current_context
def revoke_assignment_authority(actor, role_id):
    existing_admin(actor)
    role = StaffRole.objects.select_for_update(of=("self",)).select_related("membership").get(
        pk=role_id, role__in=["president", "admin", "secretary"], membership__tribunal_id=current_tribunal_id())
    lock_key(f"staff-role:{role.membership.account_id}:{role.membership.tribunal_id}")
    if role.revoked_at is None:
        role.revoked_at = timezone.now()
        role.save(update_fields=["revoked_at"])
        audit(actor, "assignment_authority_revoked", role)
    return role


def grant_assignment_presidency(actor, account_id, tribunal_id):
    return grant_assignment_authority(actor, account_id, tribunal_id, "president")

