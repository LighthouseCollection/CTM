from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Q
from .models import Application, Case, Party


def active(actor):
    if not actor or not actor.is_authenticated or not actor.is_active:
        raise PermissionDenied("An active signed-in account is required.")


def staff(actor):
    active(actor)
    if actor.role == "applicant":
        raise PermissionDenied("Council access required.")


def administrator(actor):
    active(actor)
    if actor.role not in {"admin", "secretary"}:
        raise PermissionDenied("Administrator or secretary required.")


def writer(actor, case):
    staff(actor)
    if actor.role not in {"admin", "secretary"} and case.assigned_member_id != actor.pk:
        raise PermissionDenied(
            "Only the assigned case manager can perform this action."
        )


def open_proceeding(proceeding):
    if proceeding.status != "open" or proceeding.case.status != "open":
        raise ValidationError("The original closed proceeding is read-only.")


def visible_applications(actor):
    active(actor)
    qs = Application.objects.select_related("owner", "case", "proceeding", "party")
    return (
        qs.filter(owner=actor)
        if actor.role == "applicant"
        else qs.filter(submitted_at__isnull=False)
    )


def application_for(actor, app_id, write=False):
    active(actor)
    app = Application.objects.select_related(
        "owner", "case", "proceeding", "party"
    ).get(pk=app_id)
    if app.owner_id != actor.pk:
        if actor.role == "applicant" or app.submitted_at is None:
            raise PermissionDenied("Application not accessible.")
        if write:
            administrator(actor)
    return app


def case_for(actor, case_id, write=False):
    active(actor)
    case = Case.objects.get(pk=case_id)
    if actor.role == "applicant":
        if not Party.objects.filter(case=case, account=actor).exists() or write:
            raise PermissionDenied("Case not accessible.")
    elif write:
        writer(actor, case)
    return case
