from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Max
from django.utils import timezone
from tribunal.models import (
    Account,
    Case,
    CaseAssignment,
    Proceeding,
    CaseNote,
    NoteRevision,
    FindingRevision,
    CouncilSession,
    AgendaItem,
    Hearing,
    HearingOutcome,
    Outbox,
    Party,
    TestimonyAppointment,
    AppointmentResponse,
)
from tribunal.policy import administrator, staff, writer, open_proceeding
from .common import audit, notify, notify_manager


@transaction.atomic
def assign_case(actor, case_id, member_id, president_id):
    administrator(actor)
    case = Case.objects.select_for_update(of=("self",)).get(pk=case_id)
    if case.status != "open":
        raise ValidationError("Closed case cannot be reassigned.")
    member = Account.objects.get(pk=member_id, is_active=True)
    president = Account.objects.get(pk=president_id, role="president", is_active=True)
    staff(member)
    previous = case.assigned_member
    case.assigned_member = member
    case.save(update_fields=["assigned_member"])
    record = CaseAssignment.objects.create(
        case=case, member=member, president=president, actor=actor
    )
    audit(actor, "case_assigned", record, case)
    for recipient in {x for x in [previous, member] if x}:
        notify(recipient, "assignment_changed", record, case=case)
    for party in case.parties.select_related("account").all():
        if party.account:
            notify(
                party.account,
                "assignment_changed",
                record,
                case=case,
                payload={
                    "assigned_member": f"{member.first_name} {member.last_name}".strip()
                },
            )
    return record


@transaction.atomic
def save_note(actor, proceeding_id, text, note_id=None):
    proceeding = (
        Proceeding.objects.select_for_update(of=("self",))
        .select_related("case")
        .get(pk=proceeding_id)
    )
    writer(actor, proceeding.case)
    open_proceeding(proceeding)
    if not text.strip():
        raise ValidationError("Note cannot be empty.")
    note = (
        CaseNote.objects.get(pk=note_id, proceeding=proceeding)
        if note_id
        else CaseNote.objects.create(proceeding=proceeding, author=actor)
    )
    if note.author_id != actor.pk:
        raise PermissionDenied("Only the original author can edit a note.")
    number = (
        NoteRevision.objects.filter(note=note).aggregate(n=Max("number"))["n"] or 0
    ) + 1
    revision = NoteRevision.objects.create(
        note=note, number=number, text=text, actor=actor
    )
    audit(actor, "note_saved", revision, proceeding.case)
    return note


@transaction.atomic
def save_finding(actor, proceeding_id, fact_code, value, sources=None):
    proceeding = (
        Proceeding.objects.select_for_update(of=("self",))
        .select_related("case")
        .get(pk=proceeding_id)
    )
    writer(actor, proceeding.case)
    open_proceeding(proceeding)
    number = (
        FindingRevision.objects.filter(
            proceeding=proceeding, fact_code=fact_code
        ).aggregate(n=Max("number"))["n"]
        or 0
    ) + 1
    revision = FindingRevision.objects.create(
        proceeding=proceeding,
        fact_code=fact_code,
        number=number,
        value=value,
        sources=sources or [],
        actor=actor,
    )
    audit(actor, "finding_saved", revision, proceeding.case)
    return revision


@transaction.atomic
def create_session(actor, session_date):
    administrator(actor)
    session = CouncilSession.objects.create(date=session_date)
    audit(actor, "session_created", session)
    return session


@transaction.atomic
def place_agenda(actor, session_id, case_id, part=2):
    administrator(actor)
    session = CouncilSession.objects.select_for_update(of=("self",)).get(pk=session_id)
    case = Case.objects.get(pk=case_id)
    if session.state != "planned" or part not in {1, 2}:
        raise ValidationError("Invalid session/agenda part.")
    if (
        case.status == "closed"
        and not case.applications.filter(kind="appeal", status="submitted").exists()
    ):
        raise ValidationError("Closed case has no pending appeal to hear.")
    position = (session.agenda.aggregate(n=Max("position"))["n"] or 0) + 1
    item, _ = AgendaItem.objects.get_or_create(
        session=session, case=case, defaults={"part": part, "position": position}
    )
    audit(actor, "agenda_placed", item, case)
    return item


@transaction.atomic
def close_session(actor, session_id):
    administrator(actor)
    session = CouncilSession.objects.select_for_update(of=("self",)).get(pk=session_id)
    if session.state == "closed":
        return session
    next_session = (
        CouncilSession.objects.filter(date__gt=session.date, state="planned")
        .order_by("date")
        .first()
    )
    for item in session.agenda.select_for_update(of=("self",)).all():
        if item.state in {"scheduled", "time_exhausted"}:
            item.state = "unpresented"
            item.save(update_fields=["state"])
            if next_session:
                target = place_agenda(actor, next_session.pk, item.case_id, item.part)
                target.carried_from = item
                target.save(update_fields=["carried_from"])
        # Explicit deferred and presenter_absent items deliberately await manual placement.
    session.state = "closed"
    session.closed_at = timezone.now()
    session.save(update_fields=["state", "closed_at"])
    Outbox.objects.filter(
        delivered_at__isnull=True,
        kind="message_session",
        payload__session=str(session.pk),
    ).update(due_at=timezone.now())
    audit(actor, "session_closed", session)
    return session


@transaction.atomic
def hear_case(actor, item_id):
    staff(actor)
    item = (
        AgendaItem.objects.select_for_update(of=("self",))
        .select_related("case", "session")
        .get(pk=item_id)
    )
    if item.case.assigned_member_id != actor.pk:
        raise PermissionDenied("Only the assigned member presents the hearing.")
    if item.session.state == "closed" or item.state != "scheduled":
        raise ValidationError("Agenda item cannot be heard.")
    hearing = Hearing.objects.create(
        agenda=item,
        proceeding=item.case.proceedings.filter(status="open").first(),
        presenter=actor,
    )
    item.state = "heard"
    item.save(update_fields=["state"])
    audit(actor, "case_heard", hearing, item.case)
    return hearing


@transaction.atomic
def save_hearing_outcome(
    actor, hearing_id, internal_text, recommendations, applicant_message=None
):
    hearing = Hearing.objects.select_related("agenda__case").get(pk=hearing_id)
    writer(actor, hearing.agenda.case)
    if hearing.proceeding:
        open_proceeding(hearing.proceeding)
    prior = HearingOutcome.objects.filter(hearing=hearing).exists()
    result = HearingOutcome.objects.create(
        hearing=hearing,
        internal_text=internal_text,
        recommendations=recommendations,
        actor=actor,
    )
    if not prior:
        from .communications import send_message

        party_ids = list(
            hearing.agenda.case.parties.filter(account__isnull=False).values_list(
                "pk", flat=True
            )
        )
        body = f"Your case was presented on {hearing.agenda.session.date}. Your case is still pending."
        if applicant_message:
            body += "\n\n" + applicant_message
        if party_ids:
            send_message(actor, hearing.agenda.case_id, body, party_ids)
    audit(actor, "hearing_outcome_saved", result, hearing.agenda.case)
    return result


@transaction.atomic
def schedule_testimony(actor, agenda_id, party_id, starts_at, ends_at, instructions):
    agenda = (
        AgendaItem.objects.select_for_update(of=("self",))
        .select_related("case")
        .get(pk=agenda_id)
    )
    CouncilSession.objects.select_for_update(of=("self",)).get(pk=agenda.session_id)
    writer(actor, agenda.case)
    party = Party.objects.get(pk=party_id, case=agenda.case, account__isnull=False)
    if (
        agenda.session.state != "planned"
        or starts_at >= ends_at
        or starts_at.date() != agenda.session.date
    ):
        raise ValidationError(
            "Use non-overlapping testimony times on the session date."
        )
    if (
        TestimonyAppointment.objects.filter(
            agenda__session=agenda.session, starts_at__lt=ends_at, ends_at__gt=starts_at
        )
        .exclude(state="cancelled")
        .exists()
    ):
        raise ValidationError(
            "Another applicant's testimony overlaps this appointment."
        )
    appointment = TestimonyAppointment.objects.create(
        agenda=agenda,
        party=party,
        starts_at=starts_at,
        ends_at=ends_at,
        instructions=instructions,
    )
    notify(
        party.account,
        "testimony_invited",
        appointment,
        case=agenda.case,
        payload={"starts_at": starts_at.isoformat(), "instructions": instructions},
    )
    audit(actor, "testimony_scheduled", appointment, agenda.case)
    return appointment


@transaction.atomic
def respond_testimony(actor, appointment_id, version, response, explanation=""):
    appointment = (
        TestimonyAppointment.objects.select_for_update(of=("self",))
        .select_related("party", "agenda__case")
        .get(pk=appointment_id)
    )
    if appointment.party.account_id != actor.pk:
        raise PermissionDenied("Not your testimony invitation.")
    if (
        version != appointment.version
        or appointment.state == "cancelled"
        or response not in {"confirm", "reject"}
    ):
        raise ValidationError("Invalid or superseded invitation response.")
    record = AppointmentResponse.objects.create(
        appointment=appointment,
        version=version,
        actor=actor,
        response=response,
        explanation=explanation,
    )
    notify_manager(appointment.agenda.case, "testimony_response", record)
    return record
