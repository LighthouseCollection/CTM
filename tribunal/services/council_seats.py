"""Council seats, separate from the system role - #175, D-0043.

Any staff account can hold a seat, voting or non-voting. Admin, secretary and
president change seats; each change is an append-only CouncilSeatChange row
(the latest counts) plus an audit entry. On PostgreSQL the seat comes from
public.ctm_council_seat, the same function the vote guard uses, so the
service and the database never disagree. With no change recorded, member and
president hold voting seats and secretary and admin hold none.
"""
import json

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import connection, transaction

from tribunal.db.context import database_actor
from tribunal.models import Account, CouncilSeatChange
from tribunal.policy import active, staff
from tribunal.services.common import audit

STAFF_ROLES = ("member", "president", "secretary", "admin")
SEAT_EDITORS = {"admin", "secretary", "president"}
NO_SEAT = {"seated": False, "voting": False}


def _default(account):
    voting = account.role in {"member", "president"}
    return {"seated": voting, "voting": voting}


def council_seat(account):
    """The account's current seat: {"seated": bool, "voting": bool}."""
    if connection.vendor == "postgresql":
        with connection.cursor() as cursor:
            cursor.execute("SELECT public.ctm_council_seat(%s)", [str(account.pk)])
            value = cursor.fetchone()[0]
        value = json.loads(value) if isinstance(value, str) else value
        return {"seated": bool(value["seated"]), "voting": bool(value["voting"])}
    if not account.is_active or account.role not in STAFF_ROLES:
        return dict(NO_SEAT)
    latest = CouncilSeatChange.objects.filter(account=account).order_by("-created_at", "-id").first()
    return {"seated": latest.seated, "voting": latest.voting} if latest else _default(account)


def voting_seat(account):
    return council_seat(account)["voting"]


def active_staff():
    return Account.objects.filter(is_active=True, role__in=STAFF_ROLES)


def seated_ids():
    """Ids of active staff accounts that hold a seat now."""
    return {account.pk for account in active_staff() if council_seat(account)["seated"]}


def voting_seat_count():
    return sum(1 for account in active_staff() if council_seat(account)["voting"])


@transaction.atomic
def set_seat(actor, account_id, *, seated, voting):
    active(actor)
    if actor.role not in SEAT_EDITORS:
        raise PermissionDenied("Only an administrator, the secretary or the president may change council seats.")
    if type(seated) is not bool or type(voting) is not bool:
        raise ValidationError("Seat and voting must be true or false.")
    if voting and not seated:
        raise ValidationError("A voting member must hold a council seat.")
    account = Account.objects.get(pk=account_id)
    if not account.is_active or account.role not in STAFF_ROLES:
        raise ValidationError("Only an active council account can hold a seat.")
    wanted = {"seated": seated, "voting": voting}
    if council_seat(account) == wanted:
        return wanted
    with database_actor(actor):
        change = CouncilSeatChange.objects.create(account=account, seated=seated, voting=voting, actor=actor)
    audit(actor, "council_seat_changed", change)
    return council_seat(account)


def seat_list(actor):
    staff(actor)
    rows = []
    for account in active_staff().order_by("last_name", "first_name", "pk"):
        rows.append({"id": str(account.pk), "name": f"{account.first_name} {account.last_name}".strip(),
                     "role": account.role, **council_seat(account)})
    return {"items": rows, "can_edit": actor.role in SEAT_EDITORS}
