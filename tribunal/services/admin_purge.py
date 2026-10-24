from django.core.exceptions import PermissionDenied
from django.db import connection, transaction

from tribunal.db.context import database_actor, database_settings
from tribunal.models import Case


@transaction.atomic
def purge_case(actor, case_id):
    """Permanently remove one case and every record owned by that case."""
    if not actor or not actor.is_authenticated or not actor.is_active or actor.role != "admin":
        raise PermissionDenied("Only an administrator may delete a case.")
    case = Case.objects.select_for_update().get(pk=case_id)
    with database_actor(actor), database_settings({"ctm.admin_purge_case": str(case.pk)}):
        with connection.cursor() as cursor:
            cursor.execute("SELECT public.ctm_purge_case(%s)", [str(case.pk)])
    return case.number
