from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone
from tribunal.models import (
    HistoricalWorkspace,
    Case,
    Party,
    Proceeding,
    Account,
    OpenCaseClaim,
)
from tribunal.policy import active, administrator
from .common import audit, lock_key


@transaction.atomic
def stage(actor, payload, workspace_id=None):
    administrator(actor)
    if actor.role != "admin":
        raise PermissionDenied("Initial historical entry requires administrator.")
    if not isinstance(payload, dict):
        raise ValidationError("Invalid historical entry.")
    record = (
        HistoricalWorkspace.objects.select_for_update(of=("self",)).get(
            pk=workspace_id, actor=actor
        )
        if workspace_id
        else HistoricalWorkspace(actor=actor)
    )
    if record.finalized_case_id:
        raise ValidationError("Historical entry already published.")
    record.payload = payload
    record.save()
    return record


@transaction.atomic
def publish(actor, workspace_id):
    administrator(actor)
    if actor.role != "admin":
        raise PermissionDenied("Historical finalization requires administrator.")
    record = HistoricalWorkspace.objects.select_for_update(of=("self",)).get(
        pk=workspace_id
    )
    if record.finalized_case_id:
        return record.finalized_case
    payload = record.payload
    if not str(payload.get("number", "")).strip() or payload.get("status") not in {
        "open",
        "closed",
    }:
        raise ValidationError(
            "Preserve original case number and explicitly choose open or closed."
        )
    people = []
    for party in payload.get("parties", []):
        if party.get("slot") not in {"A", "B"}:
            raise ValidationError("Invalid party slot.")
        account = (
            Account.objects.get(pk=party["account_id"], role="applicant")
            if party.get("account_id")
            else None
        )
        people.append((party, account))
    for _, account in sorted(people, key=lambda x: str(x[1].person_id) if x[1] else ""):
        if account:
            lock_key(f"person:{account.person_id}")
            if (
                payload["status"] == "open"
                and OpenCaseClaim.objects.filter(person=account.person).exists()
            ):
                raise ValidationError(
                    "Historical open case conflicts with another open case."
                )
    case = Case.objects.create(
        number=payload["number"],
        status=payload["status"],
        origin="historical",
        closed_at=timezone.now() if payload["status"] == "closed" else None,
    )
    Proceeding.objects.create(case=case, status=case.status, closed_at=case.closed_at)
    for party, account in people:
        Party.objects.create(
            case=case,
            slot=party["slot"],
            person=account.person if account else None,
            account=account,
            name=party.get("name", ""),
            reference=party.get("legacy_reference", ""),
            participating=bool(account),
        )
        if account and case.status == "open":
            OpenCaseClaim.objects.create(person=account.person, case=case)
    record.finalized_case = case
    record.save(update_fields=["finalized_case"])
    audit(
        actor,
        "historical_case_published",
        case,
        case,
        metadata={"workspace": str(record.pk), "original_dates_not_inferred": True},
    )
    return case
