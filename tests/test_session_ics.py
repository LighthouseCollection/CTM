"""#116 / D-0036 AC-2, AC-3: the council session calendar file.

No database: the builder takes a session-like object and the sequence number
(the counter itself lives on CouncilSession, owned by ctm3-database-engineer).
"""
import uuid
from datetime import date, datetime, timezone
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest

from tribunal.services.session_calendar import build_session_ics

LA = ZoneInfo("America/Los_Angeles")
SESSION_ID = uuid.UUID("0f0e0d0c-0b0a-4908-8706-050403020100")


def session(**overrides):
    values = dict(
        pk=SESSION_ID,
        date=date(2030, 2, 2),
        starts_at=datetime(2030, 2, 2, 10, 30, tzinfo=LA),
        location="St. Mark Coptic Orthodox Church, Los Angeles; Hall 2",
    )
    values.update(overrides)
    return SimpleNamespace(**values)


def parse(ics: bytes):
    """Minimal RFC 5545 reader: CRLF lines, unfolding, one VEVENT."""
    text = ics.decode("utf-8")
    assert text.endswith("\r\n")
    raw = text.split("\r\n")[:-1]
    assert all(len(line.encode("utf-8")) <= 75 for line in raw), "lines must be folded at 75 octets"
    lines = []
    for line in raw:
        if line.startswith(" "):
            lines[-1] += line[1:]
        else:
            lines.append(line)
    assert lines[0] == "BEGIN:VCALENDAR" and lines[-1] == "END:VCALENDAR"
    assert lines.count("BEGIN:VEVENT") == 1 and lines.count("END:VEVENT") == 1
    calendar, event, target = {}, {}, None
    for line in lines[1:-1]:
        if line == "BEGIN:VEVENT":
            target = event
            continue
        if line == "END:VEVENT":
            target = None
            continue
        name, _, value = line.partition(":")
        (event if target is event else calendar)[name] = value
    return calendar, event


def unescape(value):
    return value.replace("\\n", "\n").replace("\\,", ",").replace("\\;", ";").replace("\\\\", "\\")


def test_invite_is_a_publish_calendar_entry_in_utc():
    calendar, event = parse(build_session_ics(session(), sequence=0))
    assert calendar["VERSION"] == "2.0"
    assert calendar["PRODID"]
    assert calendar["METHOD"] == "PUBLISH"
    assert event["UID"] == f"council-session-{SESSION_ID}@ctm.lighthouseway.org"
    assert event["SEQUENCE"] == "0"
    assert event["DTSTART"] == "20300202T183000Z"
    assert event["DTEND"] == "20300202T203000Z"  # 2-hour default length
    assert event["DTSTAMP"].endswith("Z")
    assert unescape(event["SUMMARY"]) == "CTM Council Session 2030-02-02"
    assert unescape(event["LOCATION"]) == "St. Mark Coptic Orthodox Church, Los Angeles; Hall 2"
    assert event["URL"] == "https://ctm.lighthouseway.org"
    assert event["STATUS"] == "CONFIRMED"
    # PUBLISH: no RSVP machinery that would fail silently.
    assert not any(key.startswith(("ATTENDEE", "ORGANIZER", "RSVP")) for key in event)


def test_uid_is_stable_and_sequence_rises_with_changes():
    _, first = parse(build_session_ics(session(), sequence=0))
    _, moved_time = parse(build_session_ics(session(starts_at=datetime(2030, 2, 2, 12, 0, tzinfo=LA)), sequence=1))
    assert first["UID"] == moved_time["UID"]
    assert int(moved_time["SEQUENCE"]) > int(first["SEQUENCE"])
    assert moved_time["DTSTART"] == "20300202T200000Z"


def test_cancellation_keeps_the_uid():
    calendar, event = parse(build_session_ics(session(), sequence=3, cancel=True))
    _, invite = parse(build_session_ics(session(), sequence=2))
    assert calendar["METHOD"] == "CANCEL"
    assert event["STATUS"] == "CANCELLED"
    assert event["UID"] == invite["UID"]
    assert event["SEQUENCE"] == "3"


def test_dtstamp_uses_the_given_time():
    _, event = parse(build_session_ics(session(), sequence=0, now=datetime(2030, 1, 1, 8, 0, tzinfo=timezone.utc)))
    assert event["DTSTAMP"] == "20300101T080000Z"


def test_long_text_is_escaped_and_folded():
    location = "Hall, " * 40 + "line\nbreak \\ end; ok"
    _, event = parse(build_session_ics(session(location=location), sequence=0))
    assert unescape(event["LOCATION"]) == location


def test_only_the_allowed_fields_are_read():
    # Case numbers, names, agenda items or applicant data must never reach the
    # file: the builder reads only pk, date, starts_at and location.
    class Guarded(SimpleNamespace):
        def __getattribute__(self, name):
            if not name.startswith("__") and name not in {"pk", "date", "starts_at", "location"}:
                raise AssertionError(f"builder read forbidden field {name!r}")
            return super().__getattribute__(name)

    ics = build_session_ics(Guarded(**vars(session())), sequence=0)
    assert b"agenda" not in ics.lower()


@pytest.mark.parametrize("bad", [None, datetime(2030, 2, 2, 10, 30)])
def test_session_without_an_aware_start_time_has_no_calendar_file(bad):
    with pytest.raises(ValueError):
        build_session_ics(session(starts_at=bad), sequence=0)


def test_negative_sequence_is_refused():
    with pytest.raises(ValueError):
        build_session_ics(session(), sequence=-1)


def test_arabic_location_folds_on_character_boundaries():
    location = "كنيسة القديس مرقس القبطية الأرثوذكسية، لوس أنجلوس — القاعة الثانية " * 2
    _, event = parse(build_session_ics(session(location=location), sequence=0))
    assert unescape(event["LOCATION"]) == location
