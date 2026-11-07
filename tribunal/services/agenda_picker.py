"""Session agenda picker - #230.

Lists the cases that can go on one part of a session's agenda, and places
several of them in one all-or-none transaction. Placement itself stays in
services.council.place_agenda, so every existing rule applies to each case.
"""
import uuid

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from tribunal import models as m
from tribunal.policy import staff
from tribunal.services.applications import submitted_grounds

MANAGERS = {"admin", "secretary"}
PREVIEW_LENGTH = 200
BATCH_LIMIT = 50


def _part(value):
    try:
        part = int(value)
    except (TypeError, ValueError):
        part = None
    if part not in (1, 2):
        raise ValidationError("Choose agenda part 1 or 2.")
    return part


def _row(case):
    filing = (m.Application.objects.filter(case=case, kind="petition", submitted_at__isnull=False)
              .order_by("submitted_at", "id").first())
    submission = (m.Submission.objects.filter(application__case=case, application__kind="petition")
                  .select_related("revision").order_by("created_at", "id").first())
    outcome = (m.HearingOutcome.objects.filter(hearing__agenda__case=case)
               .order_by("-created_at", "-id").first())
    preview = (outcome.recommendations or "").strip()[:PREVIEW_LENGTH] if outcome else ""
    member = case.assigned_member
    return {
        "id": str(case.pk),
        "number": case.number,
        "party_names": [party.name for party in case.parties.order_by("slot", "id") if party.name],
        "filed_at": filing.submitted_at.isoformat() if filing else None,
        # First formal submission only: unsubmitted corrections never show (F08).
        "grounds": submitted_grounds(submission.revision.answers) if submission else [],
        "status": case.status,
        "assigned_member_id": str(member.pk) if member else None,
        "assigned_member": f"{member.first_name} {member.last_name}".strip() if member else None,
        "recommendation_preview": preview or None,
    }


def eligible_cases(actor, session_id, part):
    staff(actor)
    part = _part(part)
    session = m.CouncilSession.objects.get(pk=session_id)
    if part == 1 and actor.role not in MANAGERS:
        raise PermissionDenied("Only an administrator or the secretary places cases for assignment.")
    placed = m.AgendaItem.objects.filter(session=session).values_list("case_id", flat=True)
    cases = m.Case.objects.filter(status="open").exclude(pk__in=placed).select_related("assigned_member")
    if part == 1:
        cases = cases.filter(assigned_member__isnull=True)
    else:
        cases = cases.filter(assigned_member__isnull=False)
        if actor.role not in MANAGERS:
            cases = cases.filter(assigned_member=actor)
    return {"session": str(session.pk), "part": part, "items": [_row(case) for case in cases.order_by("number")]}


@transaction.atomic
def place_many(actor, session_id, part, case_ids):
    """Place every case or none: the first refusal rolls the whole batch back."""
    from tribunal.services.council import place_agenda
    staff(actor)
    part = _part(part)
    if not isinstance(case_ids, list) or not case_ids or len(case_ids) > BATCH_LIMIT:
        raise ValidationError(f"Choose between 1 and {BATCH_LIMIT} cases.")
    try:
        ids = [uuid.UUID(str(value)) for value in case_ids]
    except ValueError:
        raise ValidationError("Each case must be given by its id.") from None
    if len(set(ids)) != len(ids):
        raise ValidationError("Each case can be chosen once.")
    items = []
    for case_id in ids:
        try:
            items.append(place_agenda(actor, session_id, case_id, part))
        except ValidationError as exc:
            number = m.Case.objects.filter(pk=case_id).values_list("number", flat=True).first() or str(case_id)
            raise ValidationError(f"Case {number}: {' '.join(exc.messages)} Nothing was added.") from None
    return items
