"""Explicit council read contracts; callers authorize before entering this module."""

from tribunal import models as m
from functools import lru_cache
from pathlib import Path
import json
from zoneinfo import ZoneInfo
from django.db import connection
from django.core.exceptions import PermissionDenied, ObjectDoesNotExist
from tribunal.services.closed_filings import CLOSED_INTAKE, council_filing, pending_council_filings


def release_metadata(request, actor):
    if actor.role == "applicant" or request.kind not in {"medical", "psychological"}:
        return {}
    if connection.vendor == "postgresql":
        with connection.cursor() as cursor:
            cursor.execute("SELECT public.ctm_assessment_release_metadata(%s)", [str(request.pk)])
            value = cursor.fetchone()[0]
        return json.loads(value) if isinstance(value, str) else value
    releases = list(m.MedicalRelease.objects.filter(request=request, subject_id=request.subject.account_id))
    council = any(release.scope.get("council") is True for release in releases)
    return {"release_status": "signed" if council else "out_of_scope" if releases else "none",
            "release_scope": {"council": council} if releases else None}


def template_data(template, actor):
    version = template.templateversion_set.order_by("-number").first()
    return {"id": str(template.pk), "title": template.title, "shared": template.shared,
            "retired": template.retired, "owner_id": str(template.owner_id) if template.owner_id else None,
            "version": version.number if version else None,
            "questions": [{"code": row["code"], "version": row["version"]} for row in version.questions] if version else [],
            "can_publish": bool(actor.role in {"admin", "secretary"} and not template.shared and not template.retired),
            "can_retire": bool(not template.retired and (actor.role in {"admin", "secretary"} if template.shared else template.owner_id == actor.pk))}


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
    result = {
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
    if council_filing(app):
        result.update(appeal_data(app, actor))
    return result


def appeal_data(app, actor):
    supplements = m.AppealSupplement.objects.filter(application=app).select_related("actor").order_by("created_at", "id")
    disposition = m.AppealDisposition.objects.filter(application=app).select_related("actor").first()
    hearings = m.Hearing.objects.filter(agenda__case_id=app.case_id,
        presenter_id=app.case.assigned_member_id, state="held").select_related("agenda__session").order_by("-agenda__session__date", "-id")
    if app.origin == CLOSED_INTAKE and app.submitted_at:
        hearings = hearings.filter(created_at__gte=app.submitted_at)
    eligible = [{"id": str(row.pk), "session_date": row.agenda.session.date.isoformat()} for row in hearings]
    return {
        "supplements": [{"id": str(row.pk), "text": row.text, "manifest": row.manifest,
                         "actor": name(row.actor), "actor_id": str(row.actor_id),
                         "timestamp": row.created_at.isoformat()} for row in supplements],
        "disposition": {"id": str(disposition.pk), "result": disposition.result,
                        "explanation": disposition.explanation, "actor": name(disposition.actor),
                        "actor_id": str(disposition.actor_id), "timestamp": disposition.created_at.isoformat(),
                        "hearing_id": str(disposition.hearing_id),
                        "reopened_proceeding_id": str(disposition.reopened_proceeding_id) if disposition.reopened_proceeding_id else None} if disposition else None,
        "eligible_hearings": eligible,
        "can_record_result": bool(app.status == "submitted" and not disposition and eligible
            and actor.role != "applicant" and (actor.role in {"admin", "secretary"} or app.case.assigned_member_id == actor.pk)),
    }


def case_capabilities(case, actor):
    from tribunal.services.staff_roles import assignment_recorder

    council = actor.role != "applicant"
    write = council and (actor.role in {"admin", "secretary"} or case.assigned_member_id == actor.pk)
    hearable = case.status == "open" or pending_council_filings(case).exists()
    result = {"assigned_member_id": str(case.assigned_member_id) if case.assigned_member_id else None,
            "can_place_part2": bool(write and hearable),
            "can_assign": bool(council and assignment_recorder(actor) and case.status == "open")}
    if council:
        result["assignment_history"] = [{"id": str(row.pk), "member_id": str(row.member_id),
            "member": name(row.member), "president_id": str(row.president_id),
            "president": name(row.president), "actor_id": str(row.actor_id),
            "actor": name(row.actor), "timestamp": row.created_at.isoformat()}
            for row in m.CaseAssignment.objects.filter(case=case).select_related("member", "president", "actor").order_by("created_at", "id")]
    else:
        linked = case.parties.filter(account=actor, person_id=actor.person_id).exists()
        already_filed = case.applications.filter(owner=actor, kind="petition", submitted_at__isnull=False).exists()
        conflict = m.OpenCaseClaim.objects.filter(person_id=actor.person_id).exclude(case=case).exists()
        draft = m.Application.objects.filter(owner=actor, kind="petition", status="draft").first()
        can_start = bool(linked and not already_filed and not conflict and (not draft or draft.case_id == case.pk))
        result["can_start_petition"] = can_start
        result["can_start_closed_intake"] = can_start and case.status == "closed"
        result["released_decrees"] = released_decrees(case, actor)
    return result


def released_decrees(case, actor):
    from tribunal.services.files import authorized_file, display_filename

    rows = []
    for decree in m.Decree.objects.filter(signed_file__attachment__case=case, issued_at__isnull=False).order_by("-issued_at", "-id"):
        release = m.DecreeRelease.objects.filter(decree=decree, party__account=actor).order_by("-created_at", "-id").first()
        if not release or release.action != "release":
            continue
        try:
            file = authorized_file(actor, decree.signed_file_id)
        except (PermissionDenied, ObjectDoesNotExist):
            continue
        rows.append({"id": str(decree.pk), "reference": decree.reference,
            "language": "bilingual" if decree.language == "both" else decree.language,
            "released_at": release.created_at.isoformat(),
            "signed_file": {"id": str(file.pk), "name": display_filename(file),
                            "scan_state": "clean", "download_url": f"/api/files/{file.pk}/"}})
    return rows


def session_capabilities(session, actor):
    administrative = actor.role in {"admin", "secretary"} and session.state == "planned"
    can_reschedule = bool(administrative and not m.Hearing.objects.filter(agenda__session=session).exists()
                          and not m.AgendaTransferEvent.objects.filter(to_session=session).exists()
                          and not m.AgendaItem.objects.filter(carried_from__session=session).exists())
    return {"can_manage": administrative, "can_close": administrative,
            "can_reschedule": can_reschedule, "can_record_attendance": administrative}


def session_data(session, actor):
    return {
        "date": session.date.isoformat(),
        "reference": session.reference,
        "starts_at": session.starts_at.astimezone(ZoneInfo("America/Los_Angeles")).isoformat() if session.starts_at else None,
        "presiding_member_id": str(session.presiding_member_id) if session.presiding_member_id else None,
        "presiding_member_name": name(session.presiding_member) if session.presiding_member_id else None,
        "location": session.location or None,
        "state": session.state,
        **session_capabilities(session, actor),
    }


def hearing_writable(hearing, actor):
    case = hearing.agenda.case
    if actor.role == "applicant" or (actor.role not in {"admin", "secretary"} and case.assigned_member_id != actor.pk):
        return False
    if hearing.state != "held":
        return False
    if hearing.proceeding_id:
        return hearing.proceeding.status == "open" and case.status == "open"
    return pending_council_filings(case).exists()


def agenda_item_data(item, actor, attendance):
    from tribunal.services.filing_privacy import revision_visible

    case = item.case
    application = (
        case.applications.filter(kind="petition", submitted_at__isnull=False)
        .select_related("party", "owner")
        .order_by("-submitted_at", "-id")
        .first()
    )
    revision = application.revisions.filter(number=application.current_version).first() if application else None
    if application and actor.pk != application.owner_id and (revision is None or not revision_visible(revision)):
        formal = application.submissions.select_related("revision").order_by("-created_at", "-id").first()
        revision = formal.revision if formal else None
    grounds = revision.answers.get("grounds") if revision else None
    reason = ", ".join(str(value) for value in grounds) if isinstance(grounds, list) else str(grounds or "")
    applicant_party = application.party if application and application.party_id else (
        case.parties.filter(account_id=application.owner_id).order_by("slot").first() if application else None
    )
    applicant_name = (applicant_party.name if applicant_party else "") or (name(application.owner) if application else "")
    parties = case.parties.order_by("slot")
    respondent = parties.exclude(pk=applicant_party.pk).first() if applicant_party else None
    married_years = None
    if case.marriage_date:
        married_years = item.session.date.year - case.marriage_date.year - (
            (item.session.date.month, item.session.date.day) < (case.marriage_date.month, case.marriage_date.day)
        )
    hearing = m.Hearing.objects.filter(agenda=item).select_related("proceeding", "agenda__case").first()
    presenter = attendance.get(actor.pk)
    can_present = bool(case.assigned_member_id == actor.pk and item.part == 2
                       and item.state == "scheduled" and item.session.state == "planned"
                       and presenter and presenter.present
                       and (case.proceedings.filter(status="open").exists()
                            or pending_council_filings(case).exists()))
    testimony = []
    for appointment in m.TestimonyAppointment.objects.filter(agenda=item).select_related("party").order_by("starts_at", "id"):
        response = m.AppointmentResponse.objects.filter(appointment=appointment, version=appointment.version).order_by("-created_at", "-id").first()
        testimony.append({"id": str(appointment.pk), "party_id": str(appointment.party_id),
                          "party_name": appointment.party.name, "starts_at": appointment.starts_at.isoformat(),
                          "ends_at": appointment.ends_at.isoformat(), "instructions": appointment.instructions,
                          "version": appointment.version, "state": appointment.state,
                          "response": response.response if response else None})
    return {"id": str(item.pk), "case_id": str(case.pk), "case_number": case.number,
            "part": item.part, "position": item.position, "state": item.state,
            "hearing_id": str(hearing.pk) if hearing else None,
            "assigned_member_id": str(case.assigned_member_id) if case.assigned_member_id else None,
            "assigned_member_name": name(case.assigned_member) if case.assigned_member_id else None,
            "party_names": list(case.parties.order_by("slot").values_list("name", flat=True)),
            "applicant_name": applicant_name or None,
            "respondent_name": respondent.name if respondent else None,
            "reason": reason or None,
            "married_years": married_years,
            "submitted_at": application.submitted_at.isoformat() if application and application.submitted_at else None,
            "assignment_status": "assigned" if case.assigned_member_id else "unassigned",
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
    decree = m.Decree.objects.filter(decision=decision).select_related("signer").first()
    decree_data = None
    if decree:
        releases = m.DecreeRelease.objects.filter(decree=decree).select_related("actor").order_by("created_at", "id")
        decree_data = {"id": str(decree.pk), "reference": decree.reference,
                       "language": decree.language, "issued_at": decree.issued_at.isoformat() if decree.issued_at else None,
                       "signer": name(decree.signer), "signer_id": str(decree.signer_id),
                       "signed_file_id": str(decree.signed_file_id),
                       "releases": [{"party_id": str(row.party_id), "action": row.action,
                                     "actor": name(row.actor), "actor_id": str(row.actor_id),
                                     "timestamp": row.created_at.isoformat()} for row in releases]}
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
            "approval_history": approvals, "current": current, "decree": decree_data,
            "can_vote": writable, "can_approve": writable and actor.role in {"president", "admin", "secretary"}}
