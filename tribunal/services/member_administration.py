"""Explicit admin enrollment and attributed council display-name corrections."""
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count, IntegerField, OuterRef, Subquery, Value
from django.db.models.functions import Coalesce
from tribunal.models import Account, AuditEvent, Case, StaffMembership, StaffRole, Tribunal
from tribunal.db.context import core_operation
from tribunal.validation import VersionConflict, validate_json_value
from .common import audit, lock_key
from .staff_roles import existing_admin, current_tribunal_id, current_context
from .identity import enroll_council

PROFILE_FIELDS = {'first_name', 'last_name'}
COUNCIL_ROLES = {'member', 'president', 'secretary', 'admin'}


def names(values):
    for field in PROFILE_FIELDS:
        value = values.get(field)
        if (not isinstance(value, str) or not value.strip() or len(value) > 150
                or any(ord(char) < 32 or ord(char) == 127 for char in value)):
            raise ValidationError('Council first and last names must contain1–150 characters without control characters.')
    validate_json_value(values)
    return {field: values[field].strip() for field in PROFILE_FIELDS}


def profile_version(account_id):
    return AuditEvent.objects.filter(source='tribunal.account', source_id=account_id,
                                    action='council_member_profile_changed').count()


def member_queryset():
    versions = AuditEvent.objects.filter(source='tribunal.account', source_id=OuterRef('pk'),
        action='council_member_profile_changed').order_by().values('source_id').annotate(n=Count('pk')).values('n')
    open_cases = Case.objects.filter(assigned_member_id=OuterRef('pk'), status='open').order_by().values('assigned_member_id').annotate(n=Count('pk')).values('n')
    status_versions = AuditEvent.objects.filter(source='tribunal.account', source_id=OuterRef('pk'),
        action__in=['account_suspended', 'account_reactivated']).order_by().values('source_id').annotate(n=Count('pk')).values('n')
    return Account.objects.filter(role__in=COUNCIL_ROLES).annotate(
        _profile_version=Coalesce(Subquery(versions, output_field=IntegerField()), Value(0)),
        _active_case_count=Coalesce(Subquery(open_cases, output_field=IntegerField()), Value(0)),
        _status_version=Coalesce(Subquery(status_versions, output_field=IntegerField()), Value(0)),
    )

def member_data(actor, account):
    existing_admin(actor)
    # Names and their edit version must come from one statement snapshot.
    if not hasattr(account, '_profile_version'):
        account = member_queryset().get(pk=account.pk)
    return {'id': str(account.pk), 'first_name': account.first_name, 'last_name': account.last_name,
            'email': account.email, 'role': account.role, 'active': account.is_active,
            'email_verified': account.email_verified, 'profile_version': account._profile_version,
            'active_case_count': account._active_case_count, 'status_version': account._status_version,
            'can_suspend': account.is_active and account.pk != actor.pk, 'can_reactivate': not account.is_active}


@transaction.atomic
@current_context
def create_member(actor, values):
    existing_admin(actor)
    if not isinstance(values, dict) or set(values) - (PROFILE_FIELDS | {'email', 'role', 'microsoft_subject'}):
        raise ValidationError('Unsupported member enrollment fields.')
    profile = names({key: values.get(key) for key in PROFILE_FIELDS})
    tribunal_id = current_tribunal_id()
    if not tribunal_id:
        raise ValidationError('Configure the current tribunal before creating council membership.')
    tribunal = Tribunal.objects.filter(pk=tribunal_id).first()
    if tribunal is None:
        raise ValidationError('The configured current tribunal must exist before member enrollment.')
    email = values.get('email')
    if not isinstance(email, str):
        raise ValidationError('A valid council email is required.')
    email = email.strip().lower()
    if not isinstance(values.get('role', 'member'), str) or values.get('role', 'member') not in COUNCIL_ROLES:
        raise ValidationError('Choose a supported council enrollment role.')
    lock_key(f'member-enrollment:{email}')
    if Account.objects.filter(email__iexact=email).exists():
        raise ValidationError('This email already belongs to an account; member enrollment cannot convert or replace it.')
    account = enroll_council(actor, email, profile['first_name'], profile['last_name'],
                             values.get('role', 'member'), values.get('microsoft_subject'))
    membership = StaffMembership.objects.create(account=account, tribunal=tribunal, appointed_by=actor)
    audit(actor, 'staff_membership_created', membership)
    grant = StaffRole.objects.create(membership=membership, role=account.role, granted_by=actor)
    audit(actor, 'council_enrollment_role_granted', grant)
    return account, membership, grant


@transaction.atomic
@current_context
@core_operation('member_profile')
def edit_member(actor, account_id, values):
    existing_admin(actor)
    if (not isinstance(values, dict) or set(values) - (PROFILE_FIELDS | {'expected_version'})
            or not PROFILE_FIELDS.intersection(values)):
        raise ValidationError('Supply council name fields and expected_version only.')
    expected = values.get('expected_version')
    if type(expected) is not int or expected < 0:
        raise ValidationError('expected_version must be a non-negative profile version.')
    account = Account.objects.select_for_update(of=('self',)).get(pk=account_id, role__in=COUNCIL_ROLES)
    current = profile_version(account.pk)
    if current != expected:
        raise VersionConflict(current)
    before = {key: getattr(account, key) for key in PROFILE_FIELDS}
    after = names({**before, **{key: value for key, value in values.items() if key in PROFILE_FIELDS}})
    changed = [key for key in PROFILE_FIELDS if before[key] != after[key]]
    if changed:
        for key in changed:
            setattr(account, key, after[key])
        account.save(update_fields=changed)
        audit(actor, 'council_member_profile_changed', account,
              metadata={'before': before, 'after': after, 'profile_version': current + 1})
    return account
