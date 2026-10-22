from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction, connection
from django.db.models import Max
from django.utils import timezone
from zoneinfo import ZoneInfo
from datetime import datetime
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
    Attendance,
    TestimonyAppointmentVersion,
    AgendaTransferEvent,
    Message,
)
from tribunal.policy import active, administrator, staff, writer, open_proceeding
from .common import audit, notify, notify_manager, lock_key
from .closed_filings import pending_council_filings
from tribunal.db.context import database_settings, database_actor, core_operation
from tribunal.validation import validate_json_value, revision_replay, UNBOUND_VERSION


@transaction.atomic
def assign_case(actor, case_id, member_id, president_id=None):
    """Assign a case under the configured active president when none is selected."""
    with database_actor(actor):
        if president_id is None:
            president_id = (
                Account.objects.filter(is_active=True, role="president")
                .order_by("created_at", "pk")
                .values_list("pk", flat=True)
                .first()
            )
            if president_id is None:
                raise ValidationError("An active president must authorize the assignment.")
        with database_settings({"ctm.assignment_member": str(member_id), "ctm.assignment_president": str(president_id)}):
            return _assign_case(actor, case_id, member_id, president_id)


@core_operation("assignment")
def _assign_case(actor, case_id, member_id, president_id):
    from .staff_roles import assignment_president, assignment_recorder

    active(actor)
    if not assignment_recorder(actor):
        raise PermissionDenied("Administrative assignment authority is required.")
    case = Case.objects.select_for_update(of=("self",)).get(pk=case_id)
    if case.status != "open":
        raise ValidationError("Closed case cannot be reassigned.")
    member = Account.objects.get(pk=member_id, is_active=True)
    president = Account.objects.get(pk=president_id, is_active=True)
    if not assignment_president(president):
        raise PermissionDenied("An active president must authorize the assignment.")
    staff(member)
    if member.role == "president":
        raise ValidationError("The council president cannot be assigned as a case manager.")
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
def save_note(actor, proceeding_id, text, note_id=None, *, expected_version=UNBOUND_VERSION):
    proceeding = (
        Proceeding.objects.select_for_update(of=("self",))
        .select_related("case")
        .get(pk=proceeding_id)
    )
    writer(actor, proceeding.case)
    open_proceeding(proceeding)
    if not isinstance(text, str) or not text.strip() or len(text) > 100_000:
        raise ValidationError("Note must be nonempty text up to100000 characters.")
    validate_json_value(text)
    note = (
        CaseNote.objects.get(pk=note_id, proceeding=proceeding)
        if note_id
        else CaseNote.objects.create(proceeding=proceeding, author=actor)
    )
    if note.author_id != actor.pk:
        raise PermissionDenied("Only the original author can edit a note.")
    latest = NoteRevision.objects.filter(note=note).order_by("-number").first()
    if revision_replay(latest, actor, expected_version, text=text):
        note.saved_version = latest.number
        return note
    number = latest.number + 1 if latest else 1
    revision = NoteRevision.objects.create(
        note=note, number=number, text=text, actor=actor
    )
    audit(actor, "note_saved", revision, proceeding.case)
    note.saved_version = revision.number
    return note


@transaction.atomic
def save_finding(actor, proceeding_id, fact_code, value, sources=None, *, expected_version=UNBOUND_VERSION):
    proceeding = (
        Proceeding.objects.select_for_update(of=("self",))
        .select_related("case")
        .get(pk=proceeding_id)
    )
    writer(actor, proceeding.case)
    open_proceeding(proceeding)
    if not isinstance(fact_code, str) or not fact_code.strip() or len(fact_code)>100:
        raise ValidationError("Provide a fact code of1–100 characters.")
    validate_json_value({"fact_code": fact_code, "value": value})
    sources = [] if sources is None else sources
    validate_finding_sources(actor, proceeding, sources)
    latest = FindingRevision.objects.filter(proceeding=proceeding, fact_code=fact_code).order_by("-number").first()
    if revision_replay(latest, actor, expected_version, value=value, sources=sources):
        return latest
    number = latest.number + 1 if latest else 1
    revision = FindingRevision.objects.create(
        proceeding=proceeding,
        fact_code=fact_code,
        number=number,
        value=value,
        sources=sources,
        actor=actor,
    )
    audit(actor, "finding_saved", revision, proceeding.case)
    return revision


def validate_finding_sources(actor, proceeding, sources):
    import uuid
    from tribunal.models import Report, FileVersion
    from .files import authorized_file
    from .reports import require_report_disclosure
    if not isinstance(sources, list) or len(sources)>100:
        raise ValidationError("Provide up to100 source citations as a list.")
    validate_json_value(sources)
    seen = set()
    for source in sources:
        if not isinstance(source, dict) or len(source)!=1:
            raise ValidationError("Citations require one note_id, report_id or file_id.")
        kind, value = next(iter(source.items()))
        if kind not in {"note_id", "report_id", "file_id"} or not isinstance(value, str):
            raise ValidationError("Unsupported citation identifier.")
        try:
            identifier = uuid.UUID(value)
        except ValueError:
            raise ValidationError("Invalid citation identifier.")
        if (kind, identifier) in seen:
            raise ValidationError("Source citations must be distinct.")
        seen.add((kind, identifier))
        if kind == "note_id":
            CaseNote.objects.get(pk=identifier, proceeding=proceeding)
        elif kind == "report_id":
            report = Report.objects.select_related("request__subject__account").get(pk=identifier, request__proceeding=proceeding)
            require_report_disclosure(report.request)
        else:
            file = authorized_file(actor, identifier)
            if file.attachment.case_id != proceeding.case_id or file.attachment.proceeding_id != proceeding.pk:
                raise PermissionDenied("Citation source belongs to another proceeding.")


def configured_president():
    president = (
        Account.objects.filter(is_active=True, role="president")
        .order_by("created_at", "pk")
        .first()
    )
    if president is None:
        raise ValidationError("Configure an active president before creating or editing a council session.")
    return president


@transaction.atomic
def create_session(actor, session_date, *, starts_at=None, presiding_member=None, location="", state="planned"):
    administrator(actor)
    if starts_at is not None:
        if not timezone.is_aware(starts_at):
            raise ValidationError("Session start time must include a UTC offset.")
        if starts_at.astimezone(ZoneInfo("America/Los_Angeles")).date() != session_date:
            raise ValidationError("Session start time must fall on the session date in Los Angeles.")
    # Session presidings are defined by CTM's active president configuration,
    # never selected in an individual session form.
    presiding_member = configured_president()
    location = str(location or "").strip()
    if len(location) > 300:
        raise ValidationError("Session location is too long.")
    if state not in {"draft", "planned"}:
        raise ValidationError("A new session must be draft or in session.")
    session = CouncilSession.objects.create(
        date=session_date,
        starts_at=starts_at,
        presiding_member=presiding_member,
        location=location,
        state=state,
    )
    audit(actor, "session_created", session)
    return session


@transaction.atomic
def delete_draft_session(actor, session_id):
    """Remove an unassigned draft session before it becomes a tribunal record."""
    administrator(actor)
    session = CouncilSession.objects.select_for_update().get(pk=session_id)
    if session.state != "draft":
        raise ValidationError("Only a draft session can be deleted.")
    if AgendaItem.objects.filter(session=session).exists():
        raise ValidationError("A session with agenda items is retained and cannot be deleted.")
    if Attendance.objects.filter(session=session).exists():
        raise ValidationError("A session with attendance history cannot be deleted.")
    if Message.objects.filter(session=session).exists() or AgendaTransferEvent.objects.filter(to_session=session).exists():
        raise ValidationError("A session with retained history cannot be deleted.")
    with database_actor(actor), database_settings({"ctm.delete_draft_session": str(session.pk)}):
        session.delete()


@transaction.atomic
def update_session(actor, session_id, session_date, *, starts_at=None, presiding_member=None, location=""):
    administrator(actor)
    session = CouncilSession.objects.select_for_update().get(pk=session_id)
    if session.state not in {"draft", "planned"}:
        raise ValidationError("Closed sessions cannot be edited.")
    if CouncilSession.objects.exclude(pk=session.pk).filter(date=session_date).exists():
        raise ValidationError("A council session already exists on that date.")
    if starts_at is None or not timezone.is_aware(starts_at):
        raise ValidationError("Session start time must include a UTC offset.")
    if starts_at.astimezone(ZoneInfo("America/Los_Angeles")).date() != session_date:
        raise ValidationError("Session start time must fall on the session date in Los Angeles.")
    # Session presidings are defined by CTM's active president configuration,
    # never selected in an individual session form.
    presiding_member = configured_president()
    location = str(location or "").strip()
    if not location or len(location) > 300:
        raise ValidationError("Session location is required and must be at most 300 characters.")
    session.date = session_date
    session.starts_at = starts_at
    session.presiding_member = presiding_member
    session.location = location
    # A rescheduled in-progress session becomes a draft when moved into the
    # future. Upcoming sessions must never be presented as in progress.
    if session.state == "planned" and session_date > timezone.localdate():
        session.state = "draft"
        session.save(update_fields=["date", "starts_at", "presiding_member", "location", "state"])
    else:
        session.save(update_fields=["date", "starts_at", "presiding_member", "location"])
    audit(actor, "session_updated", session)
    return session


@transaction.atomic
def activate_session(actor, session_id):
    """Make a prepared draft session the official in-session record."""
    administrator(actor)
    session = CouncilSession.objects.select_for_update().get(pk=session_id)
    if session.state == "planned":
        return session
    if session.state != "draft":
        raise ValidationError("Only a draft tribunal session can be activated.")
    session.state = "planned"
    session.save(update_fields=["state"])
    audit(actor, "session_activated", session)
    return session


@transaction.atomic
def return_session_to_planned(actor, session_id):
    """Return an in-progress session to Planned before it is adjourned."""
    administrator(actor)
    session = CouncilSession.objects.select_for_update().get(pk=session_id)
    if session.state == "draft":
        return session
    if session.state != "planned":
        raise ValidationError("Only an in-progress tribunal session can return to Planned.")
    session.state = "draft"
    session.save(update_fields=["state"])
    audit(actor, "session_returned_to_planned", session)
    return session


def attendance_for(actor, session_id, hearing_id=None):
    staff(actor)
    session = CouncilSession.objects.get(pk=session_id)
    if hearing_id:
        Hearing.objects.get(pk=hearing_id, agenda__session=session)
    rows = (
        Attendance.objects.filter(session=session, hearing_id=hearing_id)
        .select_related("member")
        .order_by("created_at", "pk")
    )
    return {row.member_id: row for row in rows}


@transaction.atomic
def record_attendance(actor, session_id, member_id, present, hearing_id=None):
    administrator(actor)
    if type(present) is not bool:
        raise ValidationError("Attendance must be true or false.")
    session = CouncilSession.objects.select_for_update().get(pk=session_id)
    if session.state == "closed":
        raise ValidationError("Closed session attendance is read-only.")
    member = Account.objects.get(pk=member_id)
    if not member.is_active or member.role == "applicant":
        raise ValidationError("Attendance requires an active council account.")
    hearing = None
    if hearing_id:
        hearing = Hearing.objects.select_related("agenda__case", "proceeding").get(
            pk=hearing_id, agenda__session=session
        )
        if hearing.state != "held":
            raise ValidationError("Attendance requires a held hearing.")
        Case.objects.select_for_update().get(pk=hearing.agenda.case_id)
        if hearing.proceeding_id:
            proceeding = (
                Proceeding.objects.select_for_update()
                .select_related("case")
                .get(pk=hearing.proceeding_id)
            )
            open_proceeding(proceeding)
        elif not pending_council_filings(hearing.agenda.case).exists():
            raise ValidationError("Completed appeal hearing attendance is read-only.")
    row = Attendance.objects.create(
        session=session, hearing=hearing, member=member, present=present, actor=actor
    )
    audit(actor, "attendance_recorded", row, hearing.agenda.case if hearing else None)
    return row


@transaction.atomic
def place_agenda(actor, session_id, case_id, part=2):
    staff(actor)
    if type(part) is not int or part not in {1, 2}:
        raise ValidationError("Invalid agenda part.")
    session = CouncilSession.objects.select_for_update(of=("self",)).get(pk=session_id)
    case = Case.objects.select_for_update(of=("self",)).get(pk=case_id)
    if part == 1:
        administrator(actor)
    else:
        writer(actor, case)
    if session.state not in {"draft", "planned"}:
        raise ValidationError("Invalid session/agenda part.")
    if (
        case.status == "closed"
        and not pending_council_filings(case).exists()
    ):
        raise ValidationError("Closed case has no pending appeal to hear.")
    active_agenda = AgendaItem.objects.select_for_update(of=("self",)).filter(
        case=case, session__state="planned", state__in={"scheduled", "time_exhausted"}
    ).exclude(session=session).first()
    if active_agenda:
        raise ValidationError("Case is tied to an in-session agenda. Use the documented transfer override.")
    position = (session.agenda.aggregate(n=Max("position"))["n"] or 0) + 1
    item, created = AgendaItem.objects.get_or_create(
        session=session, case=case, defaults={"part": part, "position": position}
    )
    if item.part != part:
        raise ValidationError(
            "Case is already in another part of this session's agenda."
        )
    if created:
        audit(actor, "agenda_placed", item, case)
    return item


@transaction.atomic
def transfer_agenda_item(actor, item_id, target_session_id, reason):
    """Move an open agenda item to a later session through an audited override."""
    if not isinstance(reason, str) or not reason.strip():
        raise ValidationError("A reason is required to move a case to another session.")
    source = (
        AgendaItem.objects.select_for_update(of=("self",))
        .select_related("case", "session")
        .get(pk=item_id)
    )
    case = Case.objects.select_for_update(of=("self",)).get(pk=source.case_id)
    writer(actor, case)
    target = CouncilSession.objects.select_for_update(of=("self",)).get(pk=target_session_id)
    if source.session.state not in {"draft", "planned"} or source.state not in {"scheduled", "time_exhausted"}:
        raise ValidationError("Only a scheduled case in an open tribunal session can be moved.")
    if target.pk == source.session_id or target.state not in {"draft", "planned"} or target.date <= source.session.date:
        raise ValidationError("Choose a later open tribunal session.")
    if AgendaItem.objects.filter(session=target, case=case).exists():
        raise ValidationError("The case is already on the selected session agenda.")
    position = (target.agenda.aggregate(n=Max("position"))["n"] or 0) + 1
    destination = AgendaItem.objects.create(
        session=target, case=case, part=source.part, position=position, carried_from=source
    )
    source_state = source.state
    source.state = "transferred"
    source.save(update_fields=["state"])
    event = AgendaTransferEvent.objects.create(
        case=case,
        from_session_snapshot={
            "session_id": str(source.session_id), "reference": source.session.reference,
            "agenda_id": str(source.pk), "part": source.part, "state": source_state,
        },
        to_session=target, destination_item=destination, reason=reason.strip(), actor=actor,
    )
    audit(actor, "agenda_transferred", event, case, metadata={
        "source_agenda_id": str(source.pk), "destination_agenda_id": str(destination.pk),
        "source_session_id": str(source.session_id), "target_session_id": str(target.pk),
    })
    return destination


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
    attendance = attendance_for(actor, session.pk)
    for item in session.agenda.select_for_update(of=("self",)).select_related("case"):
        if item.part == 1 and item.state == "scheduled" and item.case.assigned_member_id:
            item.state = "assigned"
            item.save(update_fields=["state"])
            audit(actor, "assignment_agenda_completed", item, item.case)
            continue
        if item.state in {"scheduled", "time_exhausted"}:
            presenter = attendance.get(item.case.assigned_member_id)
            if item.part == 2 and presenter is not None and not presenter.present:
                item.state = "presenter_absent"
                item.save(update_fields=["state"])
                audit(actor, "hearing_deferred_presenter_absent", item, item.case)
                continue
            item.state = "unpresented"
            item.save(update_fields=["state"])
            if next_session:
                CouncilSession.objects.select_for_update(of=("self",)).get(
                    pk=next_session.pk
                )
                existing = AgendaItem.objects.filter(
                    session=next_session, case_id=item.case_id
                ).first()
                if existing:
                    audit(
                        actor,
                        "agenda_carryover_already_placed",
                        item,
                        item.case,
                        metadata={"target_agenda_id": str(existing.pk)},
                    )
                    continue
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
def set_session_adjourned(actor, session_id, adjourned, ended_at):
    """Adjourn an in-session council session at its recorded local end time."""
    staff(actor)
    if actor.role not in {"admin", "secretary"}:
        raise PermissionDenied("Only the tribunal administrator or secretary can adjourn a session.")
    if not isinstance(ended_at, datetime) or not timezone.is_aware(ended_at):
        raise ValidationError("Session end time must include a time zone.")
    session = CouncilSession.objects.select_for_update().get(pk=session_id)
    local_end = ended_at.astimezone(ZoneInfo("America/Los_Angeles"))
    if local_end.date() != session.date:
        raise ValidationError("Session end time must fall on the session date.")
    if session.starts_at and ended_at <= session.starts_at:
        raise ValidationError("Session end time must be after the session start time.")
    if not adjourned:
        raise ValidationError("An adjourned session remains closed; open its record to take notes.")
    if session.state != "planned":
        raise ValidationError("Only an in-session tribunal session can be adjourned.")
    # Keep all normal close-side effects (agenda completion, carryovers, and
    # queued communication release) in the established command.
    session = close_session(actor, session_id)
    session.adjourned_at = ended_at
    session.save(update_fields=["adjourned_at"])
    audit(actor, "session_adjourned", session)
    return session


@transaction.atomic
def hear_case(actor, item_id):
    staff(actor)
    # Attendance edits and hearing snapshots serialize on the same session row.
    session_id = AgendaItem.objects.values_list("session_id", flat=True).get(pk=item_id)
    CouncilSession.objects.select_for_update().get(pk=session_id)
    item = (
        AgendaItem.objects.select_for_update(of=("self",))
        .select_related("case", "session")
        .get(pk=item_id)
    )
    item.case = Case.objects.select_for_update().get(pk=item.case_id)
    if item.case.assigned_member_id != actor.pk:
        raise PermissionDenied("Only the assigned member presents the hearing.")
    if item.part != 2 or item.session.state == "closed" or item.state != "scheduled":
        raise ValidationError("Agenda item cannot be heard.")
    proceeding = item.case.proceedings.select_for_update().filter(status="open").first()
    pending_appeal = pending_council_filings(item.case).exists()
    if (item.case.status != "open" or proceeding is None) and not pending_appeal:
        raise ValidationError("Case has no open proceeding or pending appeal to hear.")
    defaults = attendance_for(actor, item.session_id)
    presenter = defaults.get(actor.pk)
    if presenter is None:
        raise ValidationError(
            "Record the assigned presenter's attendance before the hearing."
        )
    if not presenter.present:
        item.state = "presenter_absent"
        item.save(update_fields=["state"])
        audit(actor, "hearing_deferred_presenter_absent", item, item.case)
        return None
    hearing = Hearing.objects.create(
        agenda=item,
        proceeding=proceeding,
        presenter=actor,
    )
    with database_settings({"ctm.hearing_snapshot": str(hearing.pk)}):
        Attendance.objects.bulk_create(
            [
                Attendance(
                    session=item.session,
                    hearing=hearing,
                    member=member,
                    present=defaults[member.pk].present
                    if member.pk in defaults
                    else False,
                    actor=actor,
                )
                for member in Account.objects.filter(is_active=True).exclude(
                    role="applicant"
                )
            ]
        )
    item.state = "heard"
    item.save(update_fields=["state"])
    audit(actor, "case_heard", hearing, item.case)
    return hearing


@transaction.atomic
def save_hearing_outcome(
    actor, hearing_id, internal_text, recommendations, applicant_message=None,
    *, email_timing="immediate", session_id=None,
):
    lock_key(f"hearing-outcome:{hearing_id}")
    hearing = Hearing.objects.select_related("agenda__case").get(pk=hearing_id)
    writer(actor, hearing.agenda.case)
    if hearing.state != "held":
        raise ValidationError("Hearing outcome requires a held hearing.")
    if hearing.proceeding:
        open_proceeding(hearing.proceeding)
    elif not pending_council_filings(hearing.agenda.case).exists():
        raise ValidationError("Completed appeal hearing is read-only.")
    prior = HearingOutcome.objects.filter(hearing=hearing).exists()
    result = HearingOutcome.objects.create(
        hearing=hearing,
        internal_text=internal_text,
        recommendations=recommendations,
        actor=actor,
    )
    if not prior:
        from .communications import send_message

        recipients = hearing.agenda.case.parties.filter(account__isnull=False)
        if hearing.proceeding_id is None:
            recipients = recipients.filter(account_id__in=pending_council_filings(hearing.agenda.case).values("owner_id"))
        party_ids = list(recipients.values_list("pk", flat=True))
        body = f"Your case was presented on {hearing.agenda.session.date}. Your case is still pending."
        if applicant_message:
            body += "\n\n" + applicant_message
        if party_ids:
            send_message(actor, hearing.agenda.case_id, body, party_ids,
                         email_timing=email_timing, session_id=session_id)
    audit(actor, "hearing_outcome_saved", result, hearing.agenda.case)
    return result


@transaction.atomic
def schedule_testimony(actor, agenda_id, party_id, starts_at, ends_at, instructions):
    session_id = AgendaItem.objects.values_list("session_id", flat=True).get(
        pk=agenda_id
    )
    CouncilSession.objects.select_for_update(of=("self",)).get(pk=session_id)
    agenda = (
        AgendaItem.objects.select_for_update(of=("self",))
        .select_related("case")
        .get(pk=agenda_id)
    )
    writer(actor, agenda.case)
    if agenda.case.status != "open" and not pending_council_filings(agenda.case).exists():
        raise ValidationError("Closed case has no pending appeal testimony.")
    party = Party.objects.get(pk=party_id, case=agenda.case, account__isnull=False)
    if (
        agenda.session.state != "planned"
        or not isinstance(starts_at, datetime) or not isinstance(ends_at, datetime)
        or not timezone.is_aware(starts_at) or not timezone.is_aware(ends_at)
        or starts_at >= ends_at
        or starts_at.astimezone(ZoneInfo("America/Los_Angeles")).date() != agenda.session.date
        or ends_at.astimezone(ZoneInfo("America/Los_Angeles")).date() != agenda.session.date
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
    version = snapshot_testimony(actor, appointment)
    notify(
        party.account,
        "testimony_invited",
        appointment,
        case=agenda.case,
        payload={"starts_at": starts_at.isoformat(), "instructions": instructions,
                 "appointment": str(appointment.pk), "version": appointment.version},
    )
    queue_testimony_reminder(appointment, version)
    audit(actor, "testimony_scheduled", appointment, agenda.case)
    return appointment


def snapshot_testimony(actor, appointment):
    session = appointment.agenda.session
    version, _ = TestimonyAppointmentVersion.objects.get_or_create(
        appointment=appointment, version=appointment.version,
        defaults={"starts_at": appointment.starts_at, "ends_at": appointment.ends_at,
                  "instructions": appointment.instructions, "cancelled": appointment.state == "cancelled",
                  "attendance_location": {"session_id": str(session.pk), "reference": session.reference,
                                          "date": session.date.isoformat()}, "actor": actor},
    )
    return version


def queue_testimony_reminder(appointment, version):
    Outbox.objects.get_or_create(key=f"testimony-reminder:{version.pk}", defaults={
        "recipient": appointment.party.account, "case": appointment.agenda.case,
        "kind": "testimony_reminder", "due_at": appointment.starts_at - timezone.timedelta(days=1),
        "payload": {"appointment": str(appointment.pk), "version": appointment.version},
    })


@transaction.atomic
def reschedule_session(actor, session_id, new_date, replacement_times, reason):
    administrator(actor)
    source = CouncilSession.objects.select_for_update(of=("self",)).get(pk=session_id)
    if not isinstance(reason, str) or not reason.strip():
        raise ValidationError("Record the reason for rescheduling.")
    if source.state != "planned" or source.date == new_date:
        raise ValidationError("Only a planned session can move to a different date.")
    if Hearing.objects.filter(agenda__session=source).exists():
        raise ValidationError("A session with a held hearing is retained history.")
    if AgendaTransferEvent.objects.filter(to_session=source).exists():
        raise ValidationError("A prior transfer targets this session; retained transfer history requires reconciliation.")
    if AgendaItem.objects.filter(carried_from__session=source).exists():
        raise ValidationError("Retained carryover history prevents deleting this session.")
    if CouncilSession.objects.filter(date=new_date).exists():
        raise ValidationError("Another council session already uses this date.")
    if not isinstance(replacement_times, dict):
        raise ValidationError("Supply replacement testimony times by appointment identifier.")
    items = list(source.agenda.select_for_update(of=("self",)).order_by("case_id"))
    for item in items:
        item.case = Case.objects.select_for_update(of=("self",)).get(pk=item.case_id)
        if item.case.status != "open" and not pending_council_filings(item.case).exists():
            raise ValidationError("Resolve a closed case agenda entry before rescheduling.")
    appointments = list(TestimonyAppointment.objects.select_for_update(of=("self",)).filter(
        agenda__session=source).select_related("party__account", "agenda__session", "agenda__case").order_by("starts_at", "id"))
    active_ids = {str(row.pk) for row in appointments if row.state != "cancelled"}
    if set(replacement_times) != active_ids:
        raise ValidationError("Provide explicit new times for every active testimony appointment.")
    spans = []
    for appointment in appointments:
        if appointment.state == "cancelled":
            continue
        times = replacement_times[str(appointment.pk)]
        starts, ends = times.get("starts_at"), times.get("ends_at")
        if (not starts or not ends or not timezone.is_aware(starts) or not timezone.is_aware(ends)
            or starts >= ends or starts.astimezone(ZoneInfo("America/Los_Angeles")).date() != new_date
            or ends.astimezone(ZoneInfo("America/Los_Angeles")).date() != new_date):
            raise ValidationError("Replacement testimony times must be aware and within the new session date.")
        if any(starts < prior_end and ends > prior_start for prior_start, prior_end in spans):
            raise ValidationError("Replacement testimony appointments overlap.")
        spans.append((starts, ends))
    starts_at = None
    if source.starts_at:
        local = source.starts_at.astimezone(ZoneInfo("America/Los_Angeles"))
        starts_at = datetime.combine(new_date, local.timetz())
    target = create_session(
        actor,
        new_date,
        starts_at=starts_at,
        presiding_member=source.presiding_member,
        location=source.location,
    )
    snapshot = {"id": str(source.pk), "date": source.date.isoformat(), "reference": source.reference,
                "attendance": [{"id": str(row.pk), "member_id": str(row.member_id), "present": row.present,
                                "actor_id": str(row.actor_id), "timestamp": row.created_at.isoformat()}
                               for row in Attendance.objects.filter(session=source, hearing__isnull=True).order_by("created_at", "id")]}
    with database_actor(actor), database_settings({"ctm.reschedule_source": str(source.pk), "ctm.reschedule_target": str(target.pk)}):
        destinations = {}
        for item in items:
            destination = AgendaItem.objects.create(session=target, case=item.case, part=item.part,
                position=item.position, state=item.state, carried_from=item.carried_from)
            destinations[item.pk] = destination
            AgendaTransferEvent.objects.create(case=item.case, from_session_snapshot={**snapshot,
                "agenda_id": str(item.pk), "part": item.part, "position": item.position, "state": item.state},
                to_session=target, destination_item=destination, reason=reason, actor=actor)
        for appointment in appointments:
            snapshot_testimony(actor, appointment)
            appointment.agenda = destinations[appointment.agenda_id]
            if appointment.state != "cancelled":
                times = replacement_times[str(appointment.pk)]
                appointment.starts_at = times["starts_at"]
                appointment.ends_at = times["ends_at"]
                appointment.version += 1
                appointment.state = "invited"
                appointment.instructions = times.get("instructions", appointment.instructions)
            appointment.save()
            if appointment.state != "cancelled":
                version = snapshot_testimony(actor, appointment)
                notify(appointment.party.account, "testimony_rescheduled", version, case=appointment.agenda.case,
                    payload={"appointment": str(appointment.pk), "version": appointment.version,
                             "starts_at": appointment.starts_at.isoformat()})
                queue_testimony_reminder(appointment, version)
        for message in Message.objects.filter(session=source).select_related("case"):
            Message.objects.filter(pk=message.pk).update(session=target,
                session_snapshot=message.session_snapshot or {key: snapshot[key] for key in ["id", "date", "reference"]})
            audit(actor, "message_session_rescheduled", message, message.case,
                  metadata={"from_session": str(source.pk), "to_session": str(target.pk)})
        for event in Outbox.objects.filter(kind="message_session", delivered_at__isnull=True,
                                            discarded_at__isnull=True, payload__session=str(source.pk)):
            event.payload = {**event.payload, "session": str(target.pk)}
            event.save(update_fields=["payload"])
        Attendance.objects.filter(session=source, hearing__isnull=True).delete()
        source.agenda.all().delete()
        source.delete()
    audit(actor, "session_rescheduled", target, metadata={"from": snapshot, "reason": reason})
    return target


@transaction.atomic
def respond_testimony(actor, appointment_id, version, response, explanation=""):
    active(actor)
    appointment = (
        TestimonyAppointment.objects.select_for_update(of=("self",))
        .select_related("party")
        .get(pk=appointment_id)
    )
    if appointment.party.account_id != actor.pk:
        raise PermissionDenied("Not your testimony invitation.")
    case_id, _, planned = invitation_context(actor, appointment)
    if (
        type(version) is not int or version != appointment.version
        or appointment.state == "cancelled"
        or not planned
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
    notify_manager(Case.objects.get(pk=case_id), "testimony_response", record)
    return record


def invitation_context(actor, appointment):
    if connection.vendor == "postgresql":
        with database_actor(actor), connection.cursor() as cursor:
            cursor.execute("SELECT * FROM public.ctm_invitation_context(%s)", [str(appointment.pk)])
            row = cursor.fetchone()
        if not row:
            raise PermissionDenied("Invitation is not accessible.")
        return row
    return appointment.party.case_id, appointment.agenda.session.date, appointment.agenda.session.state == "planned"


def own_testimony(actor):
    active(actor)
    if actor.role != "applicant":
        raise PermissionDenied("Applicant invitations required.")
    result = []
    for appointment in TestimonyAppointment.objects.filter(party__account=actor).select_related("party").order_by("starts_at", "id"):
        case_id, session_date, planned = invitation_context(actor, appointment)
        response = AppointmentResponse.objects.filter(appointment=appointment, version=appointment.version).order_by("-created_at", "-id").first()
        result.append({"id": str(appointment.pk), "case_id": str(case_id), "date": session_date.isoformat(),
            "starts_at": appointment.starts_at.isoformat(), "ends_at": appointment.ends_at.isoformat(),
            "instructions": appointment.instructions, "version": appointment.version, "state": appointment.state,
            "response": response.response if response else None,
            "can_respond": bool(planned and appointment.state != "cancelled")})
    return {"items": result}


@transaction.atomic
def cancel_testimony(actor, appointment_id, expected_version):
    staff(actor)
    source = TestimonyAppointment.objects.select_related("agenda").get(pk=appointment_id)
    CouncilSession.objects.select_for_update(of=("self",)).get(pk=source.agenda.session_id)
    case = Case.objects.select_for_update(of=("self",)).get(pk=source.agenda.case_id)
    writer(actor, case)
    appointment = TestimonyAppointment.objects.select_for_update(of=("self",)).select_related("agenda__session", "party__account").get(pk=appointment_id)
    if type(expected_version) is not int or appointment.version != expected_version:
        raise ValidationError("Reload the latest testimony invitation before cancelling.")
    if appointment.agenda.session.state != "planned" or appointment.state == "cancelled":
        raise ValidationError("This testimony invitation cannot be cancelled.")
    snapshot_testimony(actor, appointment)
    appointment.version += 1
    appointment.state = "cancelled"
    appointment.save(update_fields=["version", "state"])
    version = snapshot_testimony(actor, appointment)
    notify(appointment.party.account, "testimony_cancelled", version, case=case,
           payload={"appointment": str(appointment.pk), "version": appointment.version})
    audit(actor, "testimony_cancelled", version, case)
    return appointment
