"""Council Home data - #170 AC-5 (design.md section 4).

Council roles only, deny by default. Lists carry counts, never applicant rows
or links. A count below PRIVACY_THRESHOLD is returned as null with
suppressed: true (interim value 5 until the product lead confirms it).
"""
from django.db.models import Count, Q
from django.utils import timezone

from tribunal import models as m
from tribunal.policy import staff

PRIVACY_THRESHOLD = 5
TITLES = {"president": "presiding", "secretary": "secretary"}


def suppressed_count(value):
    """(count or None, suppressed) under the privacy threshold."""
    if value < PRIVACY_THRESHOLD:
        return None, True
    return value, False


def council_members():
    """Active president, secretary and members, plus any other seat holder."""
    from tribunal.services.council_seats import seated_ids
    return m.Account.objects.filter(
        Q(role__in=("president", "secretary", "member")) | Q(pk__in=seated_ids()), is_active=True)


def members_summary(actor):
    staff(actor)
    rank = {"president": 0, "secretary": 1}
    accounts = council_members().annotate(
        open_cases=Count("assigned_cases", filter=Q(assigned_cases__status="open"), distinct=True))
    rows = []
    for account in sorted(accounts, key=lambda a: (rank.get(a.role, 2), a.last_name, a.first_name, a.pk)):
        count, hidden = suppressed_count(account.open_cases)
        rows.append({"id": str(account.pk), "name": f"{account.first_name} {account.last_name}".strip(),
                     "title": TITLES.get(account.role, "member"), "photo_url": None,
                     "active_cases": count, "suppressed": hidden})
    return {"items": rows, "threshold": PRIVACY_THRESHOLD}


def session_card(session, actor):
    """The first upcoming session on Home: time, place, agenda size and answers (#116)."""
    from tribunal.projections import session_display_location
    from tribunal.services.session_reminders import SENDER_ROLES, council_recipients, latest_answers
    answers = latest_answers(session)
    mine = answers.get(actor.pk)
    card = {"id": str(session.pk), "date": session.date.isoformat(),
            "starts_at": session.starts_at.isoformat() if session.starts_at else None,
            "location": session_display_location(session.location) or None,
            "agenda_count": session.agenda.count(),
            "my_answer": mine.answer if mine else None, "confirmed": None, "invited": None}
    if actor.role in SENDER_ROLES:  # a member never learns how others answered (#116 AC-5)
        invited = {account.pk for account in council_recipients()}
        card["invited"] = len(invited)
        card["confirmed"] = sum(1 for member, row in answers.items() if member in invited and row.answer == "attend")
    return card


def next_step(case):
    """An EN/AR key for the next step of an open case (staff lists only)."""
    if case.status != "open":
        return None
    filings = [app for app in case.applications.all() if app.kind == "petition" and app.submitted_at]
    filing = max(filings, key=lambda app: (app.submitted_at, app.pk), default=None)
    if filing and filing.status == "submitted":
        return "case.next.completeness_review"
    if filing and filing.status == "returned":
        return "case.next.applicant_correction"
    if m.AgendaItem.objects.filter(case=case, state="scheduled", session__state__in=("draft", "planned"),
                                   session__date__gte=timezone.localdate()).exists():
        return "case.next.hearing"
    if case.assigned_member_id is None:
        return "case.next.assignment"
    return "case.next.investigation"
