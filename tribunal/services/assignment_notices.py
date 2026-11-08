"""Party notices about a case manager change - #237, ruling by ctm3-product-lead.

The parties hear about an assignment only after an undo window
(settings.CTM_ASSIGNMENT_UNDO_WINDOW_SECONDS): their email waits until then,
and their in-app notice stays hidden until then. An Undo or Change inside the
window discards the pending email and leaves the in-app notice hidden, so an
accidental click tells them nothing. After the window the notice stands, and
a later change or unassign sends them a new one, so they never keep a stale
name. The case manager's own notices are immediate, as before.
"""
from datetime import datetime, timedelta

from django.conf import settings
from django.utils import timezone

from tribunal import models as m
from tribunal.services.common import notify

KIND = "assignment_changed"
KINDS = {KIND, "case_unassigned"}  # one stream of "who manages this case" notices


def window():
    return timedelta(seconds=settings.CTM_ASSIGNMENT_UNDO_WINDOW_SECONDS)


def discard_pending(case):
    """Discard party emails still inside the window; returns how many."""
    now = timezone.now()
    parties = case.parties.exclude(account__isnull=True).values_list("account_id", flat=True)
    return m.Outbox.objects.filter(
        case=case, kind__in=KINDS, recipient_id__in=list(parties), delivered_at__isnull=True,
        discarded_at__isnull=True, due_at__gt=now,
    ).update(discarded_at=now)


def notify_parties(case, record, member, kind=KIND):
    """Tell each party (after the window) who manages the case now; member may be None."""
    issued_at = timezone.now()
    visible_after = issued_at + window()
    for party in case.parties.select_related("account").all():
        if party.account:
            notify(party.account, kind, record, case=case, due_at=visible_after, payload={
                "assigned_member": f"{member.first_name} {member.last_name}".strip() if member else None,
                "assigned_member_id": str(member.pk) if member else None,
                "issued_at": issued_at.isoformat(),
                "visible_after": visible_after.isoformat(),
            })


def party_notice_visible(notice, later_keys_after):
    """In-app rule: shown after its window, unless an Undo or Change inside the
    window superseded it (the manager differs and no later notice came after it)."""
    payload = notice.payload or {}
    if notice.kind not in KINDS or "visible_after" not in payload:
        return True
    try:
        visible_after = datetime.fromisoformat(payload["visible_after"])
    except (TypeError, ValueError):
        return False
    if timezone.now() < visible_after:
        return False
    current = str(notice.case.assigned_member_id) if notice.case and notice.case.assigned_member_id else None
    if current == payload.get("assigned_member_id"):
        return True
    return later_keys_after(notice, payload["visible_after"])
