"""#176 / D-0044: admin, president and secretary delete a case.

The database function ctm_delete_case re-checks the role, removes the case and
everything that belongs only to it, and writes the one audit entry that remains
(case number, who, when, optional reason). This service adds the typed
confirmation: the user must type the case number.
"""
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import connection, transaction

from tribunal.db.context import database_actor
from tribunal.models import Case

DELETE_ROLES = {"admin", "president", "secretary"}
REASON_LIMIT = 500


@transaction.atomic
def delete_case(actor, case_id, confirm_number, reason=None):
    if not actor or not actor.is_authenticated or not actor.is_active or actor.role not in DELETE_ROLES:
        raise PermissionDenied("Only an administrator, the president or the secretary may delete a case.")
    if reason is not None and (not isinstance(reason, str) or len(reason) > REASON_LIMIT):
        raise ValidationError(f"The reason must be plain text up to {REASON_LIMIT} characters.")
    reason = (reason or "").strip() or None
    case = Case.objects.select_for_update().get(pk=case_id)
    if not isinstance(confirm_number, str) or confirm_number.strip() != case.number:
        raise ValidationError("Type the case number exactly to confirm the delete.")
    with database_actor(actor), connection.cursor() as cursor:
        cursor.execute("SELECT public.ctm_delete_case(%s, %s)", [str(case.pk), reason])
    return case.number
