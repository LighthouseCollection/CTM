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
from .files import authorized_file
from .common import lock_key


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
    *, idempotency_key=None,
):
    case = case_for(actor, case_id)
    if not isinstance(body, str) or not body.strip() or len(body) > 100000:
        raise ValidationError("Message must contain text within the supported size.")
    if not isinstance(party_ids, list) or not party_ids or len(party_ids)>2:
        raise ValidationError("Choose one or two distinct registered recipients.")
    if not isinstance(channel, str) or not isinstance(email_timing, str):
        raise ValidationError("Choose supported communication and timing values.")
    if actor.role == "applicant" and (email_timing != "immediate" or channel != "portal"):
        raise PermissionDenied("Applicant messages use the immediate private portal thread.")
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
    if idempotency_key is not None:
        if not isinstance(idempotency_key, str) or not idempotency_key.strip() or len(idempotency_key)>100:
            raise ValidationError("Message idempotency_key must be nonempty text up to100 characters.")
        lock_key(f"message:{case.pk}:{actor.pk}:{idempotency_key}")
        previous = Message.objects.filter(case=case, sender=actor, idempotency_key=idempotency_key).first()
        if previous:
            recipients = set(str(row.party_id) for row in previous.recipients.all())
            if (previous.body == body and previous.channel == channel and previous.email_timing == email_timing
                    and str(previous.session_id or "") == str(session_id or "")
                    and previous.file_links == list(map(str, file_ids or [])) and recipients == set(map(str, party_ids))):
                return previous
            raise ValidationError("This message key already identifies different content or recipients.")
    if channel not in {"portal", "email", "call"}:
        raise ValidationError("Invalid communication channel.")
    session = None
    if email_timing == "after_session":
        session = CouncilSession.objects.get(pk=session_id, state="planned")
    elif email_timing != "immediate":
        raise ValidationError("Select immediate or after council session.")
    links = []
    if file_ids is not None and (not isinstance(file_ids, list) or len(set(map(str, file_ids))) != len(file_ids)):
        raise ValidationError("Provide distinct document identifiers as a list.")
    for file_id in file_ids or []:
        file = FileVersion.objects.select_related("attachment").get(pk=file_id)
        if file.attachment.case_id != case.pk:
            raise ValidationError("Document belongs to another case.")
        file = authorized_file(actor, file_id)
        if any(
            file.attachment.owner_id != party.account_id
            or file.attachment.visibility != "own"
            for party in parties
        ):
            raise PermissionDenied("Document link would disclose restricted material.")
        if file.attachment.report_request_id:
            raise PermissionDenied("Requested-report sources use their separate protected workflow.")
        if file.attachment.versions.order_by("-number").first().pk != file.pk:
            raise PermissionDenied("Use the current authorized document version.")
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
        idempotency_key=idempotency_key,
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
def acknowledge_message(actor, message_id):
    from tribunal.policy import active
    active(actor)
    message = Message.objects.get(pk=message_id)
    rows = MessageRecipient.objects.filter(message=message, party__account=actor)
    if not rows.exists():
        raise PermissionDenied("Only an intended recipient can acknowledge their copy.")
    rows.filter(read_at__isnull=True).update(read_at=timezone.now())
    return rows.order_by("id").first()


def message_receipts(actor, message):
    rows = message.recipients.select_related("party").order_by("id")
    if actor.role == "applicant":
        rows = rows.filter(party__account=actor)
    return [{"party_id": str(row.party_id), "read_at": row.read_at.isoformat() if row.read_at else None} for row in rows]


@transaction.atomic
def log_call(actor, case_id, party_id, occurred_at, outcome, notes=""):
    from tribunal.models import CallRecord

    case = case_for(actor, case_id, write=True)
    party = Party.objects.get(pk=party_id, case=case)
    if (not isinstance(outcome, str) or not outcome.strip() or len(outcome) > 150
            or not isinstance(notes, str) or len(notes) > 100000 or not timezone.is_aware(occurred_at)):
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
