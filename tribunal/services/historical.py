from tribunal.db.context import core_operation
from datetime import datetime
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
from tribunal.validation import validate_json_value, VersionConflict, UNBOUND_VERSION, json_equivalent


def workspace_version(record, expected_version):
    if expected_version is not UNBOUND_VERSION:
        if type(expected_version) is not int or expected_version < 1:
            raise ValidationError("expected_version must be a positive integer.")
        if expected_version != record.version:
            raise VersionConflict(record.version)


@transaction.atomic
def stage(actor, payload, workspace_id=None, *, expected_version=UNBOUND_VERSION):
    administrator(actor)
    if actor.role != "admin":
        raise PermissionDenied("Initial historical entry requires administrator.")
    if not isinstance(payload, dict):
        raise ValidationError("Invalid historical entry.")
    validate_json_value(payload)
    record = (
        HistoricalWorkspace.objects.select_for_update(of=("self",)).get(
            pk=workspace_id, actor=actor
        )
        if workspace_id
        else HistoricalWorkspace(actor=actor)
    )
    if record.finalized_case_id:
        raise ValidationError("Historical entry already published.")
    if workspace_id:
        same = json_equivalent(record.payload, payload)
        if (type(expected_version) is int and expected_version == record.version-1 and same):
            return record
        workspace_version(record, expected_version)
        if same:
            return record
        record.version += 1
    elif expected_version is not UNBOUND_VERSION:
        raise ValidationError("Use expected_version only for an existing workspace.")
    record.payload = payload
    record.save()
    return record


@transaction.atomic
@core_operation("historical")
def publish(actor, workspace_id, *, expected_version=UNBOUND_VERSION):
    administrator(actor)
    if actor.role != "admin":
        raise PermissionDenied("Historical finalization requires administrator.")
    record = HistoricalWorkspace.objects.select_for_update(of=("self",)).get(
        pk=workspace_id, actor=actor
    )
    workspace_version(record, expected_version)
    if record.finalized_case_id:
        return record.finalized_case
    payload = record.payload
    if (not isinstance(payload.get("number"), str) or len(payload["number"])>100
            or not isinstance(payload.get("parties", []), list) or len(payload.get("parties", []))>2):
        raise ValidationError("Historical number and up to two structured party rows are required.")
    if not str(payload.get("number", "")).strip() or not isinstance(payload.get("status"), str) or payload.get("status") not in {
        "open",
        "closed",
    }:
        raise ValidationError(
            "Preserve original case number and explicitly choose open or closed."
        )
    people = []
    slots = set()
    identities = set()
    for party in payload.get("parties", []):
        if not isinstance(party, dict) or party.get("slot") not in {"A", "B"} or party["slot"] in slots:
            raise ValidationError("Invalid party slot.")
        slots.add(party["slot"])
        if (not isinstance(party.get("name", ""), str) or len(party.get("name", ""))>300
                or not isinstance(party.get("legacy_reference", ""), str) or len(party.get("legacy_reference", ""))>150):
            raise ValidationError("Historical party name/reference is invalid.")
        account = (
            Account.objects.get(pk=party["account_id"], role="applicant")
            if party.get("account_id")
            else None
        )
        if account:
            if not account.person_id or not account.email_verified or not account.is_active or account.person_id in identities:
                raise ValidationError("Historical account links require distinct active verified applicant identities.")
            identities.add(account.person_id)
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
    closed_at = None
    if payload["status"] == "closed" and payload.get("closed_at"):
        try:
            closed_at = datetime.fromisoformat(payload["closed_at"])
        except (TypeError, ValueError):
            raise ValidationError(
                "Historical closure timestamp is invalid; leave it unknown if unavailable."
            )
        if not timezone.is_aware(closed_at):
            raise ValidationError(
                "A known historical closure timestamp must include its timezone."
            )
    case = Case.objects.create(
        number=payload["number"],
        status=payload["status"],
        origin="historical",
        closed_at=closed_at,
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
