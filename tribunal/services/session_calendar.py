"""Calendar file (.ics, RFC 5545) for a council session - #116, D-0036.

Holds only the session date, time, location and the sign-in link: never case
numbers, names, agenda items or applicant data. METHOD:PUBLISH (no RSVP that
CTM could not read) for invites and updates; METHOD:CANCEL with the same UID
for a cancelled or moved session. Times are UTC.
"""
from datetime import datetime, timedelta, timezone

from django.utils import timezone as django_timezone

SIGN_IN_URL = "https://ctm.lighthouseway.org"
DEFAULT_LENGTH = timedelta(hours=2)
PRODID = "-//LighthouseCollection//CTM 3.0//EN"


def session_uid(session) -> str:
    return f"council-session-{session.pk}@ctm.lighthouseway.org"


def _utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _text(value) -> str:
    return (
        str(value or "")
        .replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\r\n", "\\n")
        .replace("\n", "\\n")
    )


def _fold(line: str) -> str:
    """Fold at 75 octets without splitting a UTF-8 character."""
    out, current, size, limit = [], "", 0, 75
    for char in line:
        width = len(char.encode("utf-8"))
        if size + width > limit:
            out.append(current)
            current, size, limit = " ", 1, 75
        current += char
        size += width
    out.append(current)
    return "\r\n".join(out)


def build_session_ics(session, *, sequence: int, cancel: bool = False, now: datetime | None = None) -> bytes:
    starts_at = session.starts_at
    if starts_at is None or django_timezone.is_naive(starts_at):
        raise ValueError("A council session needs a start time with a UTC offset for a calendar file.")
    if not isinstance(sequence, int) or sequence < 0:
        raise ValueError("Calendar sequence must be a non-negative integer.")
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        f"PRODID:{PRODID}",
        "CALSCALE:GREGORIAN",
        f"METHOD:{'CANCEL' if cancel else 'PUBLISH'}",
        "BEGIN:VEVENT",
        f"UID:{session_uid(session)}",
        f"SEQUENCE:{sequence}",
        f"DTSTAMP:{_utc(now or django_timezone.now())}",
        f"DTSTART:{_utc(starts_at)}",
        f"DTEND:{_utc(starts_at + DEFAULT_LENGTH)}",
        f"SUMMARY:{_text(f'CTM Council Session {session.date.isoformat()}')}",
        f"LOCATION:{_text(session.location)}",
        f"URL:{SIGN_IN_URL}",
        f"STATUS:{'CANCELLED' if cancel else 'CONFIRMED'}",
        "END:VEVENT",
        "END:VCALENDAR",
    ]
    return ("\r\n".join(_fold(line) for line in lines) + "\r\n").encode("utf-8")
