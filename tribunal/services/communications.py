from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from tribunal.models import (
    Case,
    Party,
    Message,
    MessageRecipient,
    CouncilSession,
    FileVersion,
)
from tribunal.policy import case_for, writer
from .common import audit, notify, notify_manager


def messages_for(actor, case_id):
    case = case_for(actor, case_id)
    qs = Message.objects.filter(case=case).order_by("created_at")
    if actor.role == "applicant":
        qs = qs.filter(recipients__party__account=actor).distinct()
    return qs


@transaction.atomic
def send_message(
    actor,
    case_id,
    body,
    party_ids,
    email_timing="immediate",
    session_id=None,
    file_ids=None,
    channel="portal",
):
    case = case_for(actor, case_id)
    if not body.strip() or len(body) > 100000:
        raise ValidationError("Message must contain text within the supported size.")
    parties = list(
        Party.objects.filter(case=case, pk__in=party_ids).select_related("account")
    )
    if (
        not parties
        or len(parties) != len(set(str(x) for x in party_ids))
        or any(not p.account for p in parties)
    ):
        raise ValidationError("Recipients must be registered parties of this case.")
    if actor.role == "applicant":
        if any(p.account_id != actor.pk for p in parties):
            raise PermissionDenied(
                "Applicants can only use their own private communication thread."
            )
    else:
        writer(actor, case)
    if channel not in {"portal", "email", "call"}:
        raise ValidationError("Invalid communication channel.")
    session = None
    if email_timing == "after_session":
        session = CouncilSession.objects.get(pk=session_id, state="planned")
    elif email_timing != "immediate":
        raise ValidationError("Select immediate or after council session.")
    links = []
    for file_id in file_ids or []:
        file = FileVersion.objects.select_related("attachment").get(pk=file_id)
        if file.attachment.case_id != case.pk:
            raise ValidationError("Document belongs to another case.")
        if any(
            file.attachment.owner_id != party.account_id
            or file.attachment.visibility != "own"
            for party in parties
        ):
            raise PermissionDenied("Document link would disclose restricted material.")
        links.append(str(file.pk))
    message = Message.objects.create(
        case=case,
        sender=actor,
        body=body,
        email_timing=email_timing,
        session=session,
        session_snapshot={"id": str(session.pk), "date": session.date.isoformat(), "reference": session.reference} if session else {},
        file_links=links,
        channel=channel,
    )
    for party in parties:
        MessageRecipient.objects.create(message=message, party=party)
        if actor.role != "applicant":
            due = (
                timezone.now()
                if not session
                else timezone.now() + timezone.timedelta(days=3650)
            )
            notify(
                party.account,
                "message_session" if session else "message",
                message,
                case=case,
                payload={
                    "message": str(message.pk),
                    "session": str(session.pk) if session else None,
                },
                due_at=due,
            )
    if actor.role == "applicant":
        notify_manager(case, "applicant_message", message)
    audit(actor, "message_sent", message, case)
    return message


@transaction.atomic
def log_call(actor, case_id, party_id, occurred_at, outcome, notes=""):
    from tribunal.models import CallRecord

    case = case_for(actor, case_id, write=True)
    party = Party.objects.get(pk=party_id, case=case)
    if not outcome.strip() or not timezone.is_aware(occurred_at):
        raise ValidationError(
            "Call outcome and actual timestamp with timezone are required."
        )
    record = CallRecord.objects.create(
        case=case,
        party=party,
        actor=actor,
        occurred_at=occurred_at,
        outcome=outcome,
        notes=notes,
    )
    audit(actor, "call_recorded", record, case)
    return record
