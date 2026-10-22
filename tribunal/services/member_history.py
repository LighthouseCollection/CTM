"""Read actual appointment/assignment-grant records; never synthesize legacy history."""
from django.db.models import OuterRef, Subquery
from tribunal.models import AuditEvent, StaffRole
from .staff_roles import current_tribunal_id


def membership_scope_current(account, membership, now):
    return bool(account.is_active and membership.tribunal_id == current_tribunal_id()
                and membership.active_from <= now
                and (membership.active_until is None or membership.active_until > now))


def membership_data(account, membership, now):
    tribunal = membership.tribunal
    return {
        'id': str(membership.pk),
        'tribunal': {'id': str(tribunal.pk), 'code': tribunal.code,
                     'name_en': tribunal.name_en, 'name_ar': tribunal.name_ar},
        'appointed_by_id': str(membership.appointed_by_id),
        'recorded_at': membership.created_at.isoformat(),
        'active_from': membership.active_from.isoformat(),
        'active_until': membership.active_until.isoformat() if membership.active_until else None,
        'assignment_scope_current': membership_scope_current(account, membership, now),
    }


def role_history(account):
    revocations = AuditEvent.objects.filter(
        source='tribunal.staffrole', source_id=OuterRef('pk'),
        action='assignment_authority_revoked',
    ).order_by('-created_at', '-id')
    return StaffRole.objects.filter(membership__account=account).select_related('membership').annotate(
        revocation_event_id=Subquery(revocations.values('id')[:1]),
        revoked_by_id=Subquery(revocations.values('actor_id')[:1]),
        revocation_recorded_at=Subquery(revocations.values('created_at')[:1]),
    ).order_by('-created_at', '-id')


def role_data(account, role, now):
    event = None
    if role.revoked_at is not None and role.revocation_event_id is not None:
        event = {'id': str(role.revocation_event_id),
                 'actor_id': str(role.revoked_by_id) if role.revoked_by_id else None,
                 'timestamp': role.revocation_recorded_at.isoformat()}
    return {
        'id': str(role.pk), 'membership_id': str(role.membership_id),
        'role': role.role, 'granted_by_id': str(role.granted_by_id),
        'recorded_at': role.created_at.isoformat(),
        'revoked_at': role.revoked_at.isoformat() if role.revoked_at else None,
        'revocation_event': event,
        'assignment_authority_current': bool(
            role.role in {'president', 'admin', 'secretary'} and role.revoked_at is None
            and membership_scope_current(account, role.membership, now)),
    }
