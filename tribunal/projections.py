"""Explicit council read contracts; callers authorize before entering this module."""

from tribunal import models as m
from functools import lru_cache
from pathlib import Path
import json


@lru_cache(maxsize=1)
def question_taxonomy():
    return json.loads((Path(__file__).parent / "reference/question-taxonomy.json").read_text())["questions"]


def name(account):
    return f"{account.first_name} {account.last_name}".strip()


def questionnaire_data(questionnaire):
    if questionnaire is None:
        return None
    return {"id": str(questionnaire.pk), "version": questionnaire.number,
            "published": questionnaire.published, "definition": questionnaire.definition,
            "declaration_en": questionnaire.declaration_en, "declaration_ar": questionnaire.declaration_ar}


def staff_application_data(app, actor):
    latest = app.submissions.select_related("revision__questionnaire").order_by("-created_at", "-id").first()
    manifest = []
    if latest:
        for entry in latest.manifest:
            file_id = entry.get("id")
            file = m.FileVersion.objects.filter(pk=file_id).first()
            scan = file.technical_events.filter(task="scan").order_by("-created_at", "-id").first() if file else None
            manifest.append({"file_id": file_id, "category": entry.get("category"),
                             "name": entry.get("name"), "scan_state": scan.result if scan else "pending"})
    reviews = m.CompletenessReview.objects.filter(submission__application=app).select_related("actor").order_by("created_at", "id")
    return {
        "applicant_name": app.party.name if app.party_id else name(app.owner),
        "submitted_at": app.submitted_at.isoformat() if app.submitted_at else None,
        "submitted_version": latest.revision.number if latest else None,
        "questionnaire": questionnaire_data(latest.revision.questionnaire if latest else app.questionnaire),
        "manifest": manifest,
        "reviews": [{"result": row.result, "instructions": row.instructions,
                     "actor": name(row.actor), "timestamp": row.created_at.isoformat(),
                     "submission_id": str(row.submission_id)} for row in reviews],
        "can_review": bool(actor.role in {"admin", "secretary"} and app.kind == "petition"
                           and app.status == "submitted" and app.proceeding
                           and app.proceeding.status == "open" and app.case.status == "open"),
    }


def case_capabilities(case, actor):
    council = actor.role != "applicant"
    write = council and (actor.role in {"admin", "secretary"} or case.assigned_member_id == actor.pk)
    hearable = case.status == "open" or case.applications.filter(kind="appeal", status="submitted").exists()
    return {"assigned_member_id": str(case.assigned_member_id) if case.assigned_member_id else None,
            "can_place_part2": bool(write and hearable),
            "can_assign": bool(actor.role in {"admin", "secretary"} and case.status == "open")}


def session_capabilities(session, actor):
    administrative = actor.role in {"admin", "secretary"} and session.state == "planned"
    can_reschedule = bool(administrative and not m.Hearing.objects.filter(agenda__session=session).exists()
                          and not m.AgendaTransferEvent.objects.filter(to_session=session).exists()
                          and not m.AgendaItem.objects.filter(carried_from__session=session).exists())
    return {"can_manage": administrative, "can_close": administrative,
            "can_reschedule": can_reschedule, "can_record_attendance": administrative}


def hearing_writable(hearing, actor):
    case = hearing.agenda.case
    if actor.role == "applicant" or (actor.role not in {"admin", "secretary"} and case.assigned_member_id != actor.pk):
        return False
    if hearing.state != "held":
        return False
    if hearing.proceeding_id:
        return hearing.proceeding.status == "open" and case.status == "open"
    return case.applications.filter(kind="appeal", status="submitted").exists()


def agenda_item_data(item, actor, attendance):
    case = item.case
    hearing = m.Hearing.objects.filter(agenda=item).select_related("proceeding", "agenda__case").first()
    presenter = attendance.get(actor.pk)
    can_present = bool(case.assigned_member_id == actor.pk and item.part == 2
                       and item.state == "scheduled" and item.session.state == "planned"
                       and presenter and presenter.present
                       and (case.proceedings.filter(status="open").exists()
                            or case.applications.filter(kind="appeal", status="submitted").exists()))
    testimony = []
    for appointment in m.TestimonyAppointment.objects.filter(agenda=item).select_related("party").order_by("starts_at", "id"):
        response = m.AppointmentResponse.objects.filter(appointment=appointment, version=appointment.version).order_by("-created_at", "-id").first()
        testimony.append({"id": str(appointment.pk), "party_id": str(appointment.party_id),
                          "party_name": appointment.party.name, "starts_at": appointment.starts_at.isoformat(),
                          "ends_at": appointment.ends_at.isoformat(), "instructions": appointment.instructions,
                          "version": appointment.version, "state": appointment.state,
                          "response": response.response if response else None})
    return {"id": str(item.pk), "case_id": str(case.pk), "case_number": case.number,
            "part": item.part, "state": item.state,
            "hearing_id": str(hearing.pk) if hearing else None,
            "assigned_member_id": str(case.assigned_member_id) if case.assigned_member_id else None,
            "assigned_member_name": name(case.assigned_member) if case.assigned_member_id else None,
            "party_names": list(case.parties.order_by("slot").values_list("name", flat=True)),
            "can_present": can_present,
            "can_record_outcome": bool(hearing and hearing_writable(hearing, actor)),
            "testimony": testimony}


def hearing_data(hearing, actor):
    return {"id": str(hearing.pk), "agenda_id": str(hearing.agenda_id),
            "case_id": str(hearing.agenda.case_id), "state": hearing.state,
            "presenter_id": str(hearing.presenter_id),
            "can_record_outcome": hearing_writable(hearing, actor),
            "outcomes": [{"id": str(row.pk), "internal_text": row.internal_text,
                          "recommendations": row.recommendations, "actor": name(row.actor),
                          "actor_id": str(row.actor_id), "timestamp": row.created_at.isoformat()}
                         for row in m.HearingOutcome.objects.filter(hearing=hearing).select_related("actor").order_by("created_at", "id")]}


def decision_data(decision, actor):
    votes = []
    effective = {}
    for row in m.Vote.objects.filter(decision=decision).select_related("actor").order_by("created_at", "id"):
        vote = {"member_id": str(row.member_id), "choice": row.choice,
                "actor_id": str(row.actor_id), "actor": name(row.actor), "timestamp": row.created_at.isoformat()}
        votes.append(vote)
        effective[row.member_id] = vote
    approvals = [{"president_id": str(row.president_id), "president": name(row.president),
                  "actor": name(row.actor), "actor_id": str(row.actor_id), "timestamp": row.created_at.isoformat()}
                 for row in m.PresidentialApproval.objects.filter(decision=decision).select_related("president", "actor").order_by("created_at", "id")]
    current = not m.DecisionRevision.objects.filter(proceeding=decision.proceeding, number__gt=decision.number).exists()
    writable = bool(current and decision.proceeding.status == "open" and decision.proceeding.case.status == "open")
    return {"id": str(decision.pk), "number": decision.number, "type": decision.type,
            "grounds": decision.grounds, "entitlements": decision.entitlements,
            "conditions": decision.conditions, "actor": name(decision.actor),
            "timestamp": decision.created_at.isoformat(), "votes": list(effective.values()),
            "vote_history": votes, "approval": approvals[-1] if approvals else None,
            "approval_history": approvals, "current": current,
            "can_vote": writable, "can_approve": writable and actor.role in {"president", "admin", "secretary"}}
