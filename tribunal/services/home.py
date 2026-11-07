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


def protected_cells(rows):
    """Suppress small counts so no hidden count can be worked out by subtraction.

    rows: dicts with a raw "count". Counts below the threshold become null with
    suppressed: true. When exactly one cell is hidden, the smallest visible cell
    is hidden too, because the list's total is knowable (#170, threshold 5).
    """
    out = [dict(row, suppressed=row["count"] < PRIVACY_THRESHOLD) for row in rows]
    hidden = [row for row in out if row["suppressed"]]
    visible = [row for row in out if not row["suppressed"]]
    if len(hidden) == 1 and visible:
        min(visible, key=lambda row: row["count"])["suppressed"] = True
    for row in out:
        if row["suppressed"]:
            row["count"] = None
    return out


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
    cells = protected_cells([
        {"id": str(account.pk), "name": f"{account.first_name} {account.last_name}".strip(),
         "title": TITLES.get(account.role, "member"), "photo_url": None, "count": account.open_cases}
        for account in sorted(accounts, key=lambda a: (rank.get(a.role, 2), a.last_name, a.first_name, a.pk))])
    rows = [{**{k: v for k, v in row.items() if k != "count"}, "active_cases": row["count"]} for row in cells]
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


def statistics_summary(actor, year=None):
    """Cases per member and per ground for one year (case opened), counts only.

    Grounds come from each case's first submitted petition answers, read as
    D-0035 codes; Professional Assessments are never a source.
    """
    from zoneinfo import ZoneInfo
    from django.core.exceptions import ValidationError
    from tribunal.services.applications import GROUNDS, submitted_grounds

    staff(actor)
    la = ZoneInfo("America/Los_Angeles")
    years = sorted({row.astimezone(la).year for row in m.Case.objects.values_list("created_at", flat=True)},
                   reverse=True)
    if year in (None, ""):
        year = timezone.localdate().year
    try:
        year = int(year)
    except (TypeError, ValueError):
        raise ValidationError("Choose a year as a number.")
    if not 1900 <= year <= 2999:
        raise ValidationError("Choose a year as a number.")
    cases = [case for case in m.Case.objects.all() if case.created_at.astimezone(la).year == year]

    per_member = protected_cells([
        {"id": str(account.pk), "name": f"{account.first_name} {account.last_name}".strip(),
         "count": sum(1 for case in cases if case.assigned_member_id == account.pk)}
        for account in council_members().order_by("last_name", "first_name", "pk")])
    ground_counts = dict.fromkeys(sorted(GROUNDS), 0)
    for case in cases:
        # The first formal submission only: saved-but-unsubmitted corrections never count (F08).
        submission = (m.Submission.objects.filter(application__case=case, application__kind="petition")
                      .select_related("revision").order_by("created_at", "id").first())
        revision = submission.revision if submission else None
        for code in set(submitted_grounds(revision.answers) if revision else []):
            if code in ground_counts:
                ground_counts[code] += 1
    by_ground = protected_cells([{"code": code, "count": count} for code, count in ground_counts.items()])
    return {"year": year, "years": years, "threshold": PRIVACY_THRESHOLD,
            "cases_per_member": per_member, "cases_by_ground": by_ground}
