"""Owner F12: first petition on a linked closed case uses council reconsideration."""
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Q

CLOSED_INTAKE = "closed_case_intake"


def council_filing(app):
    return app.kind == "appeal" or app.origin == CLOSED_INTAKE


def pending_council_filings(case):
    return case.applications.filter(status="submitted").filter(Q(kind="appeal") | Q(origin=CLOSED_INTAKE))


def require_new_information(app, answers):
    if app.origin == CLOSED_INTAKE:
        value = answers.get("new_information")
        if not isinstance(value, str) or not value.strip():
            raise ValidationError("Explain the new information for council consideration of this closed case.")


def linked_never_filer(app, case):
    from tribunal.models import Application
    party = case.parties.filter(account_id=app.owner_id, person_id=app.owner.person_id).first()
    if party is None:
        raise PermissionDenied("Closed-case intake requires an existing verified spouse link.")
    if Application.objects.filter(owner_id=app.owner_id, case=case, kind="petition", submitted_at__isnull=False).exclude(pk=app.pk).exists():
        raise ValidationError("This spouse has already filed a petition for this case; use the appeal route.")
    return party
