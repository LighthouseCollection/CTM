"""Case timeline by case area - #242, D-0058.

Each event: id, kind (stable, the screen shows its EN/AR text), area (one of
AREAS), date (civil, Los Angeles) or pending, upcoming, an English title and
description, params and its source record. Council only. Sources are records
the council already sees; the applicant's facts come from the first formal
submission only (never unsubmitted corrections, F08), and message or call text
is never copied into the timeline.
"""
from datetime import date, datetime
from zoneinfo import ZoneInfo

from django.core.exceptions import PermissionDenied
from django.utils import timezone

from tribunal import models as m
from tribunal.policy import case_for, staff

AREAS = ("marriage", "application", "filing", "assign", "hearing", "decision", "decree", "comms")
LA = ZoneInfo("America/Los_Angeles")


def _civil(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.astimezone(LA).date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    try:
        return date.fromisoformat(str(value)[:10]).isoformat()
    except ValueError:
        return None


def _name(account):
    return f"{account.first_name} {account.last_name}".strip() if account else None


def _event(kind, area, when, title, description="", params=None, source=None, *, upcoming=False):
    day = _civil(when)
    return {"id": f"{kind}:{source['id'] if source else day}", "kind": kind, "area": area, "date": day,
            "pending": day is None, "upcoming": upcoming or day is None, "title": title,
            "description": description, "params": params or {}, "source": source}


def _source(record):
    return {"type": record._meta.model_name, "id": str(record.pk)}


def case_timeline(actor, case_id):
    staff(actor)
    if actor.role == "applicant":
        raise PermissionDenied("Council access required.")
    case = case_for(actor, case_id)
    today = timezone.localdate()
    events = []

    submissions = list(m.Submission.objects.filter(application__case=case, application__kind="petition")
                       .select_related("revision").order_by("created_at", "id"))
    answers = submissions[0].revision.answers if submissions else {}
    marriage = answers.get("church_marriage_date") or answers.get("marriage_date") or case.marriage_date
    if _civil(marriage):
        events.append(_event("marriage", "marriage", marriage, "Marriage", "Church marriage",
                             source={"type": "case", "id": str(case.pk)}))
    separation = answers.get("separation_date") or answers.get("date_of_separation")
    if _civil(separation):
        events.append(_event("separation", "marriage", separation, "Separation",
                             source={"type": "case", "id": str(case.pk)}))
    children = answers.get("children") if isinstance(answers.get("children"), list) else []
    finding = (m.FindingRevision.objects.filter(proceeding__case=case, fact_code="case_card.summary")
               .order_by("-number", "-id").first())
    if finding and isinstance(finding.value, dict) and "children" in finding.value:
        children = finding.value["children"] or []  # the council's latest version (#199)
    for index, child in enumerate(child for child in children if isinstance(child, dict)):
        first = str(child.get("first_name") or child.get("name") or "").strip()
        born = child.get("date_of_birth") or child.get("dob")
        if _civil(born):
            events.append(_event("child_born", "marriage", born, f"Child born: {first}".strip(": "),
                                 params={"first_name": first},
                                 source={"type": "child", "id": f"{case.pk}:{index}"}))

    for index, submission in enumerate(submissions):
        kind = "petition_submitted" if index == 0 else "petition_resubmitted"
        events.append(_event(kind, "application", submission.created_at,
                             "Petition submitted" if index == 0 else "Petition resubmitted",
                             source=_source(submission)))
    for review in m.CompletenessReview.objects.filter(submission__application__case=case).order_by("created_at"):
        accepted = review.result == "accept"
        events.append(_event("filing_accepted" if accepted else "filing_returned", "filing", review.created_at,
                             "Filing accepted" if accepted else "Returned for correction",
                             source=_source(review)))

    for record in m.CaseAssignment.objects.filter(case=case).select_related("member").order_by("created_at"):
        events.append(_event("manager_assigned", "assign", record.created_at,
                             f"Case manager assigned: {_name(record.member)}",
                             params={"member": _name(record.member)}, source=_source(record)))

    heard = set()
    for hearing in m.Hearing.objects.filter(agenda__case=case).select_related("agenda__session"):
        heard.add(hearing.agenda_id)
        session_day = hearing.agenda.session.date
        events.append(_event("hearing_held", "hearing", session_day, "Council hearing",
                             params={"session_date": session_day.isoformat()}, source=_source(hearing),
                             upcoming=session_day > today))
    for item in (m.AgendaItem.objects.filter(case=case, part=2, state="scheduled",
                                             session__state__in=("draft", "planned"), session__date__gte=today)
                 .exclude(pk__in=heard).select_related("session")):
        events.append(_event("hearing_scheduled", "hearing", item.session.date, "Hearing scheduled",
                             params={"session_date": item.session.date.isoformat()}, source=_source(item),
                             upcoming=True))
    for appointment in m.TestimonyAppointment.objects.filter(agenda__case=case).exclude(state="cancelled"):
        events.append(_event("interview_scheduled", "hearing", appointment.starts_at, "Interview",
                             source=_source(appointment), upcoming=appointment.starts_at > timezone.now()))

    decisions = list(m.DecisionRevision.objects.filter(proceeding__case=case).order_by("created_at", "number"))
    approved = set(m.PresidentialApproval.objects.filter(decision__in=decisions).values_list("decision_id", flat=True))
    for decision in decisions:
        events.append(_event("decision_recorded", "decision", decision.created_at, "Council decision recorded",
                             params={"type": decision.type}, source=_source(decision)))
    for approval in m.PresidentialApproval.objects.filter(decision__in=decisions).order_by("created_at"):
        events.append(_event("decision_approved", "decision", approval.created_at, "Approved by the president",
                             source=_source(approval)))
    latest = decisions[-1] if decisions else None
    if latest and latest.pk not in approved and latest.proceeding.status == "open":
        events.append(_event("decision_pending_approval", "decision", None, "Awaiting the president's approval",
                             source=_source(latest)))
    for decree in m.Decree.objects.filter(decision__in=decisions):
        if decree.issued_at:
            events.append(_event("decree_issued", "decree", decree.issued_at, "Decree issued",
                                 params={"reference": decree.reference}, source=_source(decree)))
        for release in m.DecreeRelease.objects.filter(decree=decree).select_related("party").order_by("created_at"):
            events.append(_event("decree_released", "decree", release.created_at, "Decree released",
                                 params={"party": release.party.name, "action": release.action},
                                 source=_source(release)))

    for message in m.Message.objects.filter(case=case).order_by("created_at"):
        events.append(_event("message_sent", "comms", message.created_at, "Message sent",
                             "Portal message to the parties", source=_source(message)))
    for call in m.CallRecord.objects.filter(case=case).order_by("occurred_at"):
        events.append(_event("call_logged", "comms", call.occurred_at, "Call logged",
                             params={"outcome": call.outcome}, source=_source(call)))

    # Pending first, then newest date first; within a day, the source order above.
    order = {id(event): index for index, event in enumerate(events)}
    pending = [e for e in events if e["date"] is None]
    dated = sorted((e for e in events if e["date"] is not None), key=lambda e: (e["date"], order[id(e)]),
                   reverse=True)
    return {"case": str(case.pk), "areas": list(AREAS), "items": pending + dated}
