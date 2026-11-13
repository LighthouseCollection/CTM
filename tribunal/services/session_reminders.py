"""Council session invites, reminders and attendance answers - #116, D-0036.

Emails go through Outbox + dispatch_outbox only. Each row carries its own
subject, body and calendar file, so the worker never reads sessions or
answers; at delivery it asks ctm_session_delivery_current whether the row is
still current (same ics_sequence, session still planned and ahead, and for a
reminder: no answer yet). Nothing here reports "sent": only delivered_at does.
"""
from datetime import timedelta
from zoneinfo import ZoneInfo

from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from tribunal.models import Account, CouncilSession, Outbox, SessionResponse
from tribunal.policy import active, administrator
from tribunal.services.common import audit, lock_key
from tribunal.services.session_calendar import SIGN_IN_URL, build_session_ics

COUNCIL_ROLES = ("member", "president", "secretary", "admin")
SENDER_ROLES = {"secretary", "president", "admin"}
SESSION_KINDS = ("session_invite", "session_update", "session_cancel", "session_reminder")
ANSWERS = {"attend", "not_attend"}
REMINDER_LEAD = timedelta(days=2)
SEND_NOW_INTERVAL = timedelta(hours=1)
LA = ZoneInfo("America/Los_Angeles")
EMAIL_UNAVAILABLE = "Email is not set up, so reminders cannot be sent."

SUBJECTS = {
    "session_invite": "CTM Council Session {date}",
    "session_update": "Updated: CTM Council Session {date}",
    "session_cancel": "Cancelled: CTM Council Session {date}",
    "session_reminder": "Reminder: CTM Council Session {date}",
}
OPENINGS = {
    "session_invite": "You are invited to the CTM council session.",
    "session_update": "The CTM council session has changed.",
    "session_cancel": "The CTM council session on this date is cancelled.",
    "session_reminder": "Reminder: the CTM council session is in two days.",
}


def email_ready() -> bool:
    return bool(settings.EMAIL_HOST)


def council_recipients():
    return Account.objects.filter(
        is_active=True, email_verified=True, role__in=COUNCIL_ROLES
    ).order_by("id")


# Arabic approved by a member on #360 (rows in docs/i18n/arabic-proposals.md); #366 puts it
# after the English in the same body. Arabic-Indic digits in the Arabic half
# (docs/i18n/arabic.md); the sign-in URL stays Latin at the end of its line.
SUBJECTS_AR = {
    "session_invite": "جلسة المجلس في CTM بتاريخ {date}",
    "session_update": "تم التحديث: جلسة المجلس في CTM بتاريخ {date}",
    "session_cancel": "تم الإلغاء: جلسة المجلس في CTM بتاريخ {date}",
    "session_reminder": "تذكير: جلسة المجلس في CTM بتاريخ {date}",
}
OPENINGS_AR = {
    "session_invite": "تمت دعوتك إلى جلسة المجلس في CTM.",
    "session_update": "طرأ تغيير على جلسة المجلس في CTM.",
    "session_cancel": "أُلغيت جلسة المجلس في CTM في هذا التاريخ.",
    "session_reminder": "تذكير: موعد جلسة المجلس في CTM بعد يومين.",
}
SIGN_IN_ATTEND = "Sign in to CTM to say whether you will attend: {url}"
SIGN_IN_DETAILS = "Sign in to CTM for details: {url}"
SIGN_IN_ATTEND_AR = "سجّل الدخول إلى CTM لتُعلمنا هل ستحضر أم لا: {url}"
SIGN_IN_DETAILS_AR = "سجّل الدخول إلى CTM للاطلاع على التفاصيل: {url}"
BODY_SEPARATOR = "\n\n---\n\n"
_ARABIC_INDIC = str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")


def arabic_digits(text: str) -> str:
    return text.translate(_ARABIC_INDIC)


def _message(kind, session):
    when = session.starts_at.astimezone(LA)
    day = session.date.isoformat()
    clock = when.strftime("%H:%M")
    attend = kind != "session_cancel"
    english = "\n".join([
        OPENINGS[kind],
        "",
        f"Date: {day}",
        f"Time: {clock} Los Angeles time",
        f"Location: {session.location}",
        "",
        (SIGN_IN_ATTEND if attend else SIGN_IN_DETAILS).format(url=SIGN_IN_URL),
    ])
    arabic = "\n".join([
        OPENINGS_AR[kind],
        "",
        f"التاريخ: {arabic_digits(day)}",
        f"الوقت: {arabic_digits(clock)} بتوقيت لوس أنجلوس",
        f"الموقع: {session.location}",
        "",
        (SIGN_IN_ATTEND_AR if attend else SIGN_IN_DETAILS_AR).format(url=SIGN_IN_URL),
    ])
    subject = f"{SUBJECTS[kind].format(date=day)} / {SUBJECTS_AR[kind].format(date=arabic_digits(day))}"
    return subject, english + BODY_SEPARATOR + arabic


def _payload(kind, session, *, manual=False):
    subject, body = _message(kind, session)
    ics = build_session_ics(session, sequence=session.ics_sequence, cancel=kind == "session_cancel")
    payload = {
        "session": str(session.pk),
        "sequence": session.ics_sequence,
        "subject": subject,
        "body": body,
        "ics": ics.decode("utf-8"),
    }
    if manual:
        payload["manual"] = True
    return payload


def _queue(kind, session, recipients, *, due_at=None, key_part=None, manual=False):
    payload = _payload(kind, session, manual=manual)
    part = key_part or str(session.ics_sequence)
    for recipient in recipients:
        Outbox.objects.get_or_create(
            key=f"{kind}:{session.pk}:{part}:{recipient.pk}",
            defaults={"recipient": recipient, "kind": kind, "payload": payload,
                      "due_at": due_at or timezone.now()},
        )


def _invitable(session):
    return session.state == "planned" and session.starts_at is not None and session.starts_at > timezone.now()


def announce_session(session, *, changed=False):
    """Queue an invite (or an update) plus the 2-day reminder for every council account.

    Call inside the transaction that made the session planned or changed it.
    Without email set up nothing is queued, so nothing can look "sent".
    """
    if not email_ready() or not _invitable(session):
        return 0
    recipients = list(council_recipients())
    _queue("session_update" if changed else "session_invite", session, recipients)
    reminder_at = session.starts_at - REMINDER_LEAD
    if reminder_at > timezone.now():
        _queue("session_reminder", session, recipients, due_at=reminder_at)
    return len(recipients)


def cancel_session_calendar(session):
    """Queue a cancellation with the same UID; call before a moved session is deleted."""
    if not email_ready() or session.starts_at is None:
        return 0
    CouncilSession.objects.filter(pk=session.pk).update(ics_sequence=session.ics_sequence + 1)
    session.ics_sequence += 1
    recipients = list(council_recipients())
    _queue("session_cancel", session, recipients)
    return len(recipients)


@transaction.atomic
def answer_session(actor, session_id, answer):
    """A council member answers for themself: attend or not_attend, until the start."""
    active(actor)
    if actor.role not in COUNCIL_ROLES:
        raise PermissionDenied("Council access required.")
    if answer not in ANSWERS:
        raise ValidationError("Choose I will attend or I will not attend.")
    session = CouncilSession.objects.get(pk=session_id)
    if session.state != "planned" or session.starts_at is None or session.starts_at <= timezone.now():
        raise ValidationError("Answers close when the session starts.")
    response = SessionResponse.objects.create(session=session, member=actor, answer=answer)
    audit(actor, "session_answered", session)
    return response


def latest_answers(session):
    """Latest answer per member (the database sets created_at)."""
    latest = {}
    for row in SessionResponse.objects.filter(session=session).order_by("member_id", "-created_at", "-id"):
        latest.setdefault(row.member_id, row)
    return latest


def session_answers(actor, session_id):
    """Secretary, president and admin see every member; a member sees only their own."""
    active(actor)
    if actor.role not in COUNCIL_ROLES:
        raise PermissionDenied("Council access required.")
    session = CouncilSession.objects.get(pk=session_id)
    latest = latest_answers(session)
    if actor.role not in SENDER_ROLES:
        own = latest.get(actor.pk)
        return {"session": str(session.pk), "email_ready": email_ready(),
                "mine": _answer_data(own)}
    members = list(council_recipients())
    rows = [{"member_id": str(m.pk), "name": f"{m.first_name} {m.last_name}".strip(),
             **(_answer_data(latest.get(m.pk)) or {"answer": None, "answered_at": None})}
            for m in members]
    return {
        "session": str(session.pk),
        "email_ready": email_ready(),
        "confirmed": sum(1 for row in rows if row["answer"] == "attend"),
        "total": len(rows),
        "members": rows,
    }


def _answer_data(row):
    if row is None:
        return None
    return {"answer": row.answer, "answered_at": row.created_at.isoformat()}


@transaction.atomic
def send_reminders_now(actor, session_id, *, now=None):
    """Secretary, president or admin: remind everyone without an answer, at most once an hour."""
    active(actor)
    if actor.role not in SENDER_ROLES:
        raise PermissionDenied("Secretary, president or administrator required.")
    if not email_ready():
        raise ValidationError(EMAIL_UNAVAILABLE)
    now = now or timezone.now()
    session = CouncilSession.objects.select_for_update().get(pk=session_id)
    if not _invitable(session):
        raise ValidationError("Reminders can be sent only before a planned session starts.")
    lock_key(f"session-reminder-now:{session.pk}")
    recent = Outbox.objects.filter(
        kind="session_reminder", payload__session=str(session.pk), payload__manual=True,
        created_at__gte=now - SEND_NOW_INTERVAL,
    ).exists()
    if recent:
        raise ValidationError("A reminder was already sent in the last hour.")
    answered = set(SessionResponse.objects.filter(session=session).values_list("member_id", flat=True))
    recipients = [m for m in council_recipients() if m.pk not in answered]
    bucket = now.astimezone(ZoneInfo("UTC")).strftime("now:%Y%m%d%H")
    _queue("session_reminder", session, recipients, key_part=bucket, manual=True)
    audit(actor, "session_reminder_sent", session)
    return len(recipients)


def delivery_current(event) -> bool:
    """Non-PostgreSQL mirror of public.ctm_session_delivery_current (worker check)."""
    session = CouncilSession.objects.filter(pk=event.payload.get("session")).first()
    sequence = event.payload.get("sequence")
    if event.kind == "session_cancel":
        return session is None or session.ics_sequence == sequence
    if (session is None or session.state != "planned" or session.starts_at is None
            or session.starts_at <= timezone.now() or session.ics_sequence != sequence):
        return False
    if event.kind == "session_reminder":
        return not SessionResponse.objects.filter(session=session, member_id=event.recipient_id).exists()
    return True
