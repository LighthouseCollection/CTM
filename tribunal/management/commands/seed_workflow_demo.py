"""Repeatable, isolated workflow snapshots; never an operational data importer."""

import hashlib
import json
import os
import struct
import uuid
import zlib
from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.utils import timezone
from tribunal import models as m
from tribunal.management.demo_content import case_story
from tribunal.services.files import write_private_original

DATASET = "ctm-western-workflow-demo-v1"
ROSTER = [
    ("H.E. Metropolitan", "Serapion", "bishopserapion@lacopts.org", "president"),
    ("Fr. Mauritius", "Mikhail", "frmauritiusmikhail@lacopts.org", "secretary"),
    ("Fr. Youhana", "Ibrahim", "fryouhanaibrahim@lacopts.org", "member"),
    ("Fr. Antony", "Attallah", "frantonyattallah@lacopts.org", "member"),
    ("Fr. Boules", "Mikhail", "frpaul@lacopts.org", "member"),
    ("Fr. Youhanna", "Youssef", "fryouhannayoussef@lacopts.org", "member"),
    ("Fr. David", "Elias", "frdavidelias@lacopts.org", "member"),
    ("Fr. Jonah", "Labib", "frjonahlabib@lacopts.org", "member"),
    ("Fr. Raphael", "Maher", "frraphaelmaher@lacopts.org", "admin"),
]
COUPLES = [
    ("James Carter", "Emily Carter", "submitted"),
    ("Daniel Brooks", "Olivia Brooks", "returned"),
    ("Michael Bennett", "Charlotte Bennett", "accepted"),
    ("William Hayes", "Amelia Hayes", "investigation"),
    ("Benjamin Parker", "Sophia Parker", "hearing"),
    ("Alexander Reed", "Grace Reed", "decision"),
    ("Henry Collins", "Isabella Collins", "closed"),
    ("Samuel Morgan", "Victoria Morgan", "appeal"),
    ("Nathan Foster", "Lauren Foster", "closed"),
    ("Ethan Mitchell", "Megan Mitchell", "appeal"),
    ("Christopher Allen", "Hannah Allen", "closed"),
]
# Extra agenda scenarios, numbered 20261020-12 onward. Each lands once, keyed by
# case number, on fresh and already-seeded databases. Session slots: "current" is
# today's session; "next"/"following" are the first two upcoming draft sessions.
# Part 2 = "Scheduled Cases for Hearing" (case manager assigned); part 1 = "Cases
# to assign" (no case manager yet).
AGENDA_COUPLES = [
    ("Ryan Sullivan", "Natalie Sullivan", "current", 2, ["abandonment"]),
    ("Kevin Turner", "Rachel Turner", "current", 2, ["infidelity"]),
    ("Brandon Hughes", "Ashley Hughes", "current", 2, ["abuse", "addiction"]),
    ("Jason Price", "Melissa Price", "current", 2, ["faith"]),
    ("Tyler Coleman", "Brittany Coleman", "current", 2, ["concealment"]),
    ("Andrew Russell", "Kayla Russell", "current", 2, ["addiction"]),
    ("Jonathan Griffin", "Stephanie Griffin", "current", 2, ["infidelity", "abandonment"]),
    ("Matthew Sanders", "Nicole Sanders", "current", 2, ["abuse"]),
    ("Joshua Bryant", "Amanda Bryant", "current", 1, ["abandonment"]),
    ("Justin Ward", "Heather Ward", "current", 1, ["faith", "concealment"]),
    ("Patrick Barnes", "Danielle Barnes", "current", 1, ["infidelity"]),
    ("Eric Henderson", "Courtney Henderson", "current", 1, ["addiction"]),
    ("Adam Fisher", "Lindsay Fisher", "current", 1, ["concealment"]),
    ("Sean Powell", "Jessica Powell", "current", 1, ["abuse"]),
    ("Aaron Jenkins", "Kimberly Jenkins", "next", 2, ["abandonment", "faith"]),
    ("Kyle Simmons", "Erin Simmons", "next", 2, ["infidelity"]),
    ("Gregory Wallace", "Tiffany Wallace", "next", 1, ["addiction", "abuse"]),
    ("Derek Graham", "Monica Graham", "next", 1, ["concealment"]),
    ("Travis Holland", "Vanessa Holland", "following", 2, ["faith"]),
    ("Brian Caldwell", "Jenna Caldwell", "following", 2, ["abuse"]),
    ("Dustin Porter", "Allison Porter", "following", 1, ["abandonment"]),
    ("Cody Warren", "Sabrina Warren", "following", 1, ["infidelity", "concealment"]),
]


def identity(label):
    return uuid.uuid5(uuid.NAMESPACE_URL, f"{DATASET}:{label}")


def pdf(title, lines):
    """Generate a valid simple PDF, without real seals/signatures or external I/O."""
    escaped = lambda value: (
        str(value).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    )
    text = [
        "CTM document preview",
        title,
        *lines,
        "Unsigned preview - no signature or seal applied.",
    ]
    content = (
        "BT /F1 13 Tf 45 790 Td "
        + " ".join(f"({escaped(line)}) Tj 0 -24 Td" for line in text)
        + " ET"
    ).encode("ascii", "replace")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length "
        + str(len(content)).encode()
        + b" >>\nstream\n"
        + content
        + b"\nendstream",
    ]
    data = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for number, obj in enumerate(objects, 1):
        offsets.append(len(data))
        data.extend(f"{number} 0 obj\n".encode() + obj + b"\nendobj\n")
    xref = len(data)
    data.extend(f"xref\n0 {len(offsets)}\n0000000000 65535 f \n".encode())
    for offset in offsets[1:]:
        data.extend(f"{offset:010d} 00000 n \n".encode())
    data.extend(
        f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    )
    return bytes(data)


def placeholder_png():
    def chunk(kind, payload):
        return (
            struct.pack(">I", len(payload))
            + kind
            + payload
            + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)
        )

    pixels = b"".join(b"\x00" + bytes([190, 190, 190]) * 64 for _ in range(64))
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", 64, 64, 8, 2, 0, 0, 0))
        + chunk(b"tEXt", b"Description\x00DEMO placeholder - not a real person")
        + chunk(b"IDAT", zlib.compress(pixels))
        + chunk(b"IEND", b"")
    )


QUESTIONNAIRE_FIELDS = [
    {
        "code": "first_name",
        "type": "text",
        "required": True,
        "label_en": "First name",
        "label_ar": "الاسم الأول",
    },
    {
        "code": "last_name",
        "type": "text",
        "required": True,
        "label_en": "Last name",
        "label_ar": "اسم العائلة",
    },
    {
        "code": "birth_date",
        "type": "date",
        "required": True,
        "label_en": "Date of birth",
        "label_ar": "تاريخ الميلاد",
    },
    {
        "code": "gender",
        # The applicant form and server validator only know `choice` (#104).
        "type": "choice",
        "choices": ["M", "F"],
        "choice_labels": {
            "M": {"label_en": "Male", "label_ar": "ذكر"},
            "F": {"label_en": "Female", "label_ar": "أنثى"},
        },
        "label_en": "Gender",
        "label_ar": "النوع",
    },
    {
        "code": "marriage_date",
        "type": "date",
        "required": True,
        "label_en": "Marriage date",
        "label_ar": "تاريخ الزواج",
    },
    {
        "code": "statement",
        "type": "textarea",
        "required": True,
        "label_en": "Petition statement",
        "label_ar": "بيان الطلب",
    },
]


def renderable_definition(definition):
    """True when both the server validator and the applicant form accept it."""
    from django.core.exceptions import ValidationError
    from tribunal.services.configuration import validate_questionnaire_definition

    try:
        validate_questionnaire_definition(definition)
    except ValidationError:
        return False
    fields = definition.get("fields", [])
    return all(
        isinstance(field.get(key), str) and field[key].strip()
        for field in fields
        for key in ("label_en", "label_ar")
    ) and all(
        isinstance(labels.get(key), str) and labels[key].strip()
        for field in fields
        for choice in field.get("choices", [])
        for labels in [field.get("choice_labels", {}).get(choice, {})]
        for key in ("label_en", "label_ar")
    )


def supersede_unrenderable_questionnaires():
    """Republish this dataset's schema when an older seed stored an invalid one.

    Questionnaire versions are immutable, so a corrected version is appended and
    only unsubmitted drafts move to it; submitted provenance stays pinned.
    """
    for purpose in ("petition", "appeal"):
        versions = m.QuestionnaireVersion.objects.filter(purpose=purpose)
        broken = [
            version
            for version in versions.filter(definition__dataset=DATASET).order_by("number")
            if not renderable_definition(version.definition)
        ]
        if not broken:
            continue
        target = versions.filter(published=True).order_by("-number").first()
        if target is None or target in broken:
            latest = versions.order_by("-number").first()
            target = m.QuestionnaireVersion.objects.create(
                purpose=purpose,
                number=latest.number + 1,
                definition={**broken[-1].definition, "fields": QUESTIONNAIRE_FIELDS},
                declaration_en=broken[-1].declaration_en,
                declaration_ar=broken[-1].declaration_ar,
                published=True,
            )
        m.Application.objects.filter(
            questionnaire__in=broken, submitted_at__isnull=True
        ).update(questionnaire=target)


class Command(BaseCommand):
    help = "Populate an explicitly opted-in fictitious Western-name workflow dataset."

    def add_arguments(self, parser):
        parser.add_argument(
            "--live-fictitious",
            action="store_true",
            help="Permit this synthetic fixture in a designated live demo database.",
        )
        parser.add_argument(
            "--confirmation",
            default="",
            help="Required literal confirmation for the live fictitious dataset.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        live_fictitious = options["live_fictitious"]
        isolated_demo = (
            os.environ.get("CTM_SYNTHETIC_DEMO") == "true"
            and os.environ.get("CTM_ENVIRONMENT") == "test"
            and connection.vendor == "sqlite"
        )
        if live_fictitious:
            if options["confirmation"] != "FICTITIOUS-DEMO-DATA-ONLY":
                raise CommandError("Live fixture confirmation did not match.")
            if connection.vendor != "postgresql":
                raise CommandError("The live fictitious fixture requires PostgreSQL.")
            if m.Case.objects.exclude(origin__in={"synthetic", "demo"}).exists():
                raise CommandError("Refusing to mix live fixtures with non-demo cases.")
        elif not isolated_demo:
            raise CommandError("Explicit isolated synthetic demo environment required.")
        if not live_fictitious and connection.vendor != "sqlite":
            raise CommandError(
                "This review seed only supports isolated SQLite; no operational database writes."
            )
        allowed_origins = {"synthetic", "demo"} if live_fictitious else {"synthetic"}
        if m.Case.objects.exclude(origin__in=allowed_origins).exists():
            raise CommandError("Refusing to mix workflow fixtures with non-demo cases.")
        roster = []
        for first, last, email, role in ROSTER:
            account = m.Account.objects.filter(email__iexact=email).first()
            if account and account.role != role and not live_fictitious:
                raise CommandError(
                    f"Existing staff role conflict: {email}; no automatic role changes."
                )
            if account is None:
                account = m.Account.objects.create_user(
                    email=email, first_name=first, last_name=last, role=role
                )
            elif account.role != role:
                account.role = role
                account.save(update_fields=["role"])
            roster.append(account)
        president, secretary = roster[:2]
        admin = roster[-1]
        members = roster[2:8]
        now = timezone.now()
        today = timezone.localdate()

        def session_at(day, *, state, hour, location):
            starts_at = timezone.make_aware(
                datetime.combine(day, time(hour=hour)), ZoneInfo("America/Los_Angeles")
            )
            session, _ = m.CouncilSession.objects.get_or_create(date=day)
            if session.state == "closed":
                # Archived sessions are immutable; an idempotent fixture refresh
                # must leave their recorded council context untouched.
                return session
            session.state = state
            session.starts_at = starts_at
            session.presiding_member = president
            session.location = location
            session.closed_at = now if state == "closed" else None
            session.save(update_fields=["state", "starts_at", "presiding_member", "location", "closed_at"])
            for member in roster[:-1]:
                if not m.Attendance.objects.filter(session=session, member=member).exists():
                    m.Attendance.objects.create(
                        session=session,
                        member=member,
                        actor=admin,
                        present=member != members[-1],
                    )
            return session

        def ensure_session_agenda(current_session, archived_session):
            entries = (
                (current_session, "20261020-03", 1, 1, "scheduled"),
                (current_session, "20261020-04", 2, 1, "scheduled"),
                (archived_session, "20261020-07", 2, 1, "presented"),
            )
            for session, number, part, position, state in entries:
                case = m.Case.objects.filter(number=number, origin="synthetic").first()
                if not case:
                    continue
                agenda, _ = m.AgendaItem.objects.get_or_create(
                    session=session,
                    case=case,
                    defaults={"part": part, "position": position, "state": state},
                )
                if (agenda.part, agenda.position, agenda.state) != (part, position, state):
                    agenda.part, agenda.position, agenda.state = part, position, state
                    agenda.save(update_fields=["part", "position", "state"])

        current_session = session_at(
            today,
            state="planned",
            hour=10,
            location="St. George Coptic Orthodox Church, Bellflower, California",
        )
        existing_upcoming = (
            m.CouncilSession.objects.filter(state="draft", date__gt=today)
            .order_by("date")
            .first()
        )
        session = session_at(
            existing_upcoming.date if existing_upcoming else today + timedelta(days=7),
            state="draft",
            hour=10,
            location="St. George Coptic Orthodox Church, Bellflower, California",
        )
        archived_session = session_at(
            today - timedelta(days=14),
            state="closed",
            hour=10,
            location="St. George Coptic Orthodox Church, Bellflower, California",
        )
        # Keep each session workspace populated during live review: Current,
        # Upcoming, and Archived each show at least five fictitious records.
        for offset in range(1, 5):
            session_at(
                today - timedelta(days=offset),
                state="planned",
                hour=10,
                location="St. George Coptic Orthodox Church, Bellflower, California",
            )
            session_at(
                today + timedelta(days=7 * (offset + 1)),
                state="draft",
                hour=10,
                location="St. George Coptic Orthodox Church, Bellflower, California",
            )
            session_at(
                today - timedelta(days=14 * (offset + 1)),
                state="closed",
                hour=10,
                location="St. George Coptic Orthodox Church, Bellflower, California",
            )

        def profile_answers(owner):
            """Fictional submitted answers used by the profile and marriage projections."""
            return {
                "other_names": "—",
                "birth_country": "Egypt",
                "nationality": "Egyptian",
                "awareness_of_application": "—",
                "address": "1842 Maple Dr, Bellflower, California, 90706, United States",
                "mobile": "(562) 555-1042",
                "email": owner.email,
                "immigration_status": "Citizen",
                "residing_with": "Alone",
                "education": "Bachelor of Business Administration",
                "graduation_year": "2007",
                "occupation": "Registered Nurse",
                "denomination": "Coptic Orthodox",
                "name_of_bishop": "H.E. Metropolitan Serapion",
                "diocese": "Los Angeles, Southern California and Hawaii",
                "parish_name": "St. Mary Coptic Orthodox Church, Bellflower",
                "father_of_confession": "Fr. Abraam Mikhail",
                "spouse_other_names": "—",
                "spouse_birth_country": "Egypt",
                "spouse_nationality": "Egyptian",
                "spouse_awareness_of_application": "—",
                "spouse_address": "88 Park Ave, Anaheim, California, 92805, United States",
                "spouse_mobile": "(714) 555-0142",
                "spouse_email": "spouse@example.test",
                "spouse_immigration_status": "Citizen",
                "spouse_residing_with": "Alone",
                "spouse_education": "Bachelor of Arts in Education",
                "spouse_graduation_year": "2011",
                "spouse_occupation": "Teacher",
                "spouse_denomination": "Coptic Orthodox",
                "spouse_name_of_bishop": "H.E. Metropolitan Serapion",
                "spouse_diocese": "Los Angeles, Southern California and Hawaii",
                "spouse_parish_name": "St. Mary Coptic Orthodox Church, Bellflower",
                "spouse_father_of_confession": "Fr. Abraam Mikhail",
                "married_outside_coptic_church": "No",
                "religious_denomination_officiating": "—",
                "date_of_marriage_outside_coptic_church": "—",
                "church_marriage_date": "2010-06-12",
                "officiating_priest": "Fr. Antony Attallah",
                "church_name": "St. Mark Coptic Orthodox Church",
                "church_location": "Los Angeles, CA",
                "marriage_diocese": "Diocese of Los Angeles",
            }

        def repair_synthetic_photo_originals():
            """Restore missing image originals in the opted-in local demo media tree."""
            files = m.FileVersion.objects.filter(
                attachment__case__origin="synthetic",
                attachment__category__in={"PHOTO", "SPOUSE_PHOTO"},
                mime_type="image/png",
            )
            for file in files:
                target = Path(settings.MEDIA_ROOT) / file.object_key
                if not target.exists():
                    write_private_original(target, placeholder_png())

        dataset_exists = m.AuditEvent.objects.filter(
            action="demo_dataset_created", metadata__dataset=DATASET
        ).exists()
        schemas = {}

        def applicant(name, index, gender, birth=None):
            first, last = name.split(" ", 1)
            person = m.Person.objects.create(
                first_name=first,
                last_name=last,
                birth_date=birth or date(1980 + index, 3, 14),
                gender=gender,
            )
            return m.Account.objects.create_user(
                email=f"{first.lower()}.{last.lower()}.{index}@ctm.example.test",
                first_name=first,
                last_name=last,
                person=person,
                email_verified=True,
            )

        def source(app, category, title, version=1, attachment=None):
            attachment = attachment or m.Attachment.objects.create(
                application=app,
                case=app.case,
                proceeding=app.proceeding,
                owner=app.owner,
                category=category,
                context="demo",
                visibility="own",
            )
            image = category in {"PHOTO", "SPOUSE_PHOTO"}
            data = (
                placeholder_png()
                if image
                else pdf(
                    title,
                    [
                        f"Case: {app.case.number if app.case else 'Private draft'}",
                        f"Applicant: {app.owner.first_name} {app.owner.last_name}",
                        "Prepared for case review.",
                    ],
                )
            )
            key = f"{DATASET}/{identity(str(attachment.pk) + ':' + str(version))}.{'png' if image else 'pdf'}"
            write_private_original(Path(settings.MEDIA_ROOT) / key, data)
            file = m.FileVersion.objects.create(
                attachment=attachment,
                number=version,
                object_key=key,
                original_name=f"{category}.{'png' if image else 'pdf'}",
                display_name=f"{app.case.number if app.case else 'DRAFT'}-{category}-20261021-1200.{'png' if image else 'pdf'}",
                mime_type="image/png" if image else "application/pdf",
                byte_count=len(data),
                sha256=hashlib.sha256(data).hexdigest(),
                actor=app.owner,
                scan_state="clean",
            )
            m.FileTechnicalEvent.objects.create(
                file=file,
                task="scan",
                result="clean",
                metadata={
                    "dataset": DATASET,
                    "test_policy": True,
                    "not_live_antivirus": True,
                },
            )
            return file

        def filing(owner, case, proceeding, party, status, kind="petition", grounds=None, statement=None):
            app = m.Application.objects.create(
                owner=owner,
                case=case,
                proceeding=proceeding,
                party=party,
                kind=kind,
                status=status,
                current_version=1,
                questionnaire=schemas[kind],
                submitted_at=None if status == "draft" else now,
            )
            answers = {
                "first_name": owner.first_name,
                "last_name": owner.last_name,
                "birth_date": owner.person.birth_date.isoformat(),
                "gender": owner.person.gender,
                "marriage_date": case.marriage_date.isoformat()
                if case
                else "2014-06-15",
                # Profile answers are supplied by the seeded filing rather than
                # synthesized by the council view.
                **profile_answers(owner),
                "grounds": grounds or ["abandonment"],
                "statement": statement or "I request council consideration following our separation. We have been living apart since March 2025 despite attempts at reconciliation.",
                "new_information": "Additional correspondence was located after the original decision.",
            }
            revision = m.AnswerRevision.objects.create(
                application=app,
                number=1,
                answers=answers,
                actor=owner,
                questionnaire=schemas[kind],
            )
            m.FeeObligation.objects.create(
                application=app,
                status="due" if status == "draft" else "waived",
                waived_by=None if status == "draft" else admin,
            )
            if status != "draft":
                files = [
                    source(app, category, f"{category}")
                    for category in ("MC", "CMC", "CDD", "PHOTO", "SPOUSE_PHOTO")
                ]
                submission = m.Submission.objects.create(
                    application=app,
                    revision=revision,
                    idempotency_key=f"{DATASET}:{app.pk}",
                    actor=owner,
                    manifest=[
                        {"id": str(f.pk), "sha256": f.sha256} for f in files
                    ],
                    attestation={
                        "dataset": DATASET,
                        "demo_only": True,
                        "declaration_en": schemas[kind].declaration_en,
                    },
                )
                if status in ("accepted", "returned"):
                    m.CompletenessReview.objects.create(
                        submission=submission,
                        actor=secretary,
                        result="reject" if status == "returned" else "accept",
                        instructions="Please upload a legible marriage certificate."
                        if status == "returned"
                        else "",
                    )
            return app

        def enrich_case(index, case, manager, grounds):
            """Add varied fictitious notes, messages, calls, report and outcome text.

            Create-only and keyed by an audit marker per case, so a re-run adds
            nothing twice and no immutable row is ever rewritten.
            """
            if m.AuditEvent.objects.filter(
                case=case, action="demo_case_enriched", metadata__dataset=DATASET
            ).exists():
                return False
            party = case.parties.filter(slot="A").select_related("account").first()
            spouse = case.parties.filter(slot="B").first()
            if party is None or party.account is None:
                return False
            proceeding = case.proceedings.order_by("created_at", "id").first()
            open_file = proceeding is not None and proceeding.status == "open"
            story = case_story(
                index,
                party.name,
                (spouse.name.split(" ", 1)[0] if spouse and spouse.name else "my spouse"),
                grounds,
                case.marriage_date.year if case.marriage_date else 2012,
            )
            writer = manager or secretary
            start = now - timedelta(days=75 - index % 20)
            if open_file:
                texts = story["notes"] if manager else story["secretary_notes"]
                for step, text in enumerate(texts):
                    at = start + timedelta(days=4 * step + 1, hours=step)
                    note = m.CaseNote.objects.create(proceeding=proceeding, author=writer, created_at=at)
                    m.NoteRevision.objects.create(note=note, number=1, text=text, actor=writer, created_at=at)
            for step, (side, body) in enumerate(story["messages"]):
                at = start + timedelta(days=3 * step + 2, hours=9 + step)
                message = m.Message.objects.create(
                    case=case,
                    sender=writer if side == "staff" else party.account,
                    body=body,
                    created_at=at,
                )
                m.MessageRecipient.objects.create(
                    message=message, party=party, read_at=at + timedelta(hours=5)
                )
            for step, (direction, outcome, notes) in enumerate(story["calls"]):
                at = start + timedelta(days=5 * step + 6, hours=14)
                m.CallRecord.objects.create(
                    case=case, party=party, actor=writer, occurred_at=at,
                    direction=direction, outcome=outcome, notes=notes, created_at=at,
                )
            if open_file and manager:
                report = m.Report.objects.filter(request__case=case).select_related("request").first()
                if report is None:
                    request = m.ReportRequest.objects.create(
                        case=case,
                        proceeding=proceeding,
                        subject=party,
                        author=manager,
                        title="Marriage circumstances interview",
                        kind="interview",
                        state="completed",
                        questions=[
                            {
                                "code": "DEMO-IDENTITY",
                                "en": "Please confirm your full name.",
                                "ar": "يرجى تأكيد اسمك بالكامل.",
                            }
                        ],
                        created_at=start + timedelta(days=9),
                    )
                    report = m.Report.objects.create(
                        request=request,
                        author=manager,
                        identifier=f"{case.number}-REPORT-{timezone.localdate():%Y%m%d}",
                    )
                number = (report.revisions.order_by("-number").values_list("number", flat=True).first() or 0) + 1
                m.ReportRevision.objects.create(
                    report=report,
                    number=number,
                    actor=report.author or manager,
                    answers={"DEMO-IDENTITY": party.name},
                    observations=story["observations"],
                )
                for hearing in m.Hearing.objects.filter(agenda__case=case).select_related("presenter"):
                    internal, recommendation = story["outcome"]
                    presenter = f"{hearing.presenter.first_name} {hearing.presenter.last_name}".strip()
                    m.HearingOutcome.objects.create(
                        hearing=hearing,
                        actor=hearing.presenter,
                        internal_text=internal.format(**story["facts"], presenter=presenter),
                        recommendations=recommendation.format(**story["facts"], presenter=presenter),
                    )
            m.AuditEvent.objects.create(
                case=case,
                actor=admin,
                action="demo_case_enriched",
                source="demo_seed",
                source_id=case.pk,
                metadata={"dataset": DATASET, "not_real_proceedings": True},
            )
            return True

        def enrich_original_cases():
            count = 0
            for index, _couple in enumerate(COUPLES, 1):
                case = m.Case.objects.filter(
                    number=f"20261020-{index:02d}", origin="synthetic"
                ).select_related("assigned_member").first()
                if case and enrich_case(index, case, case.assigned_member, ["abandonment"]):
                    count += 1
            return count

        def seed_agenda_cases(current):
            """Create the AGENDA_COUPLES cases once each, keyed by case number."""
            upcoming = list(
                m.CouncilSession.objects.filter(state="draft", date__gt=today).order_by("date")[:2]
            )
            targets = {
                "current": current,
                "next": upcoming[0] if upcoming else None,
                "following": upcoming[1] if len(upcoming) > 1 else None,
            }
            added = []
            for offset, (name_a, name_b, slot, part, grounds) in enumerate(AGENDA_COUPLES):
                index = len(COUPLES) + 1 + offset
                number = f"20261020-{index:02d}"
                agenda_session = targets[slot]
                if m.Case.objects.filter(number=number).exists():
                    continue
                if agenda_session is None or agenda_session.state not in {"draft", "planned"}:
                    continue
                married_year = 1999 + (offset * 3) % 20
                a = applicant(name_a, 100 + index, "M", birth=date(married_year - 27 - offset % 4, 1 + offset % 12, 3 + offset))
                b = applicant(name_b, 200 + index, "F", birth=date(married_year - 25 - offset % 3, 12 - offset % 12, 25 - offset))
                manager = members[offset % 5] if part == 2 else None
                case = m.Case.objects.create(
                    id=identity(f"case:{index}"),
                    number=number,
                    origin="synthetic",
                    status="open",
                    marriage_date=date(married_year, 1 + (offset * 5) % 12, 1 + (offset * 7) % 27),
                    spouse_dob_low=min(a.person.birth_date, b.person.birth_date),
                    spouse_dob_high=max(a.person.birth_date, b.person.birth_date),
                    assigned_member=manager,
                )
                proceeding = m.Proceeding.objects.create(case=case, status="open")
                parties = []
                for party_slot, owner in (("A", a), ("B", b)):
                    parties.append(
                        m.Party.objects.create(
                            case=case,
                            person=owner.person,
                            account=owner,
                            slot=party_slot,
                            name=f"{owner.first_name} {owner.last_name}",
                            participating=True,
                            reference=f"{case.number}-{owner.first_name[0]}{owner.last_name[0]}{owner.person.birth_date:%Y%m%d}{owner.person.gender}",
                        )
                    )
                    m.OpenCaseClaim.objects.create(person=owner.person, case=case)
                story = case_story(index, name_a, name_b.split(" ", 1)[0], grounds, married_year)
                filing(
                    a, case, proceeding, parties[0], "accepted",
                    grounds=grounds, statement=story["statement"],
                )
                if manager:
                    m.CaseAssignment.objects.create(
                        case=case, member=manager, president=president, actor=secretary
                    )
                position = (
                    agenda_session.agenda.order_by("-position").values_list("position", flat=True).first() or 0
                ) + 1
                m.AgendaItem.objects.create(
                    session=agenda_session, case=case, part=part, position=position, state="scheduled"
                )
                enrich_case(index, case, manager, grounds)
                m.AuditEvent.objects.create(
                    case=case,
                    actor=admin,
                    action="demo_scenario_loaded",
                    source="demo_seed",
                    source_id=case.pk,
                    metadata={
                        "dataset": DATASET,
                        "stage": "agenda",
                        "session": agenda_session.date.isoformat(),
                        "part": part,
                        "not_real_proceedings": True,
                    },
                )
                added.append(number)
            return added

        if dataset_exists:
            # A fixture upgrade may add fields to the immutable-source projection.
            # This database is explicitly synthetic and isolated; production filings
            # are never updated by this command.
            for app in m.Application.objects.filter(
                case__origin="synthetic", kind="petition"
            ).select_related("owner"):
                revision = app.revisions.filter(number=app.current_version).first()
                if revision:
                    answers = {**revision.answers, **profile_answers(app.owner)}
                    # PostgreSQL immutable-row triggers reject this rewrite outright, which
                    # aborted every live re-run; only the SQLite review fixture can refresh.
                    if answers != revision.answers and connection.vendor != "postgresql":
                        # AnswerRevision intentionally blocks normal historical writes.
                        # This direct fixture repair is reachable only after the isolated
                        # synthetic-dataset guard above has already passed.
                        m.AnswerRevision.objects.filter(pk=revision.pk).update(answers=answers)
            repair_synthetic_photo_originals()
            supersede_unrenderable_questionnaires()
            ensure_session_agenda(current_session, archived_session)
            for purpose in ("petition", "appeal"):
                published = m.QuestionnaireVersion.objects.filter(
                    purpose=purpose, published=True
                ).order_by("-number")
                schemas[purpose] = (
                    published.filter(definition__dataset=DATASET).first() or published.first()
                )
            added = seed_agenda_cases(current_session)
            enriched = enrich_original_cases()
            self.stdout.write(
                "Dataset already exists; synthetic session scenarios, profile fixtures, and photo originals refreshed. "
                f"Added {len(added)} agenda cases; enriched {enriched} existing cases."
            )
            return
        fields = QUESTIONNAIRE_FIELDS
        for purpose in ("petition", "appeal"):
            latest = (
                m.QuestionnaireVersion.objects.filter(purpose=purpose)
                .order_by("-number")
                .first()
            )
            schemas[purpose] = m.QuestionnaireVersion.objects.create(
                purpose=purpose,
                number=(latest.number + 1 if latest else 1),
                definition={
                    "dataset": DATASET,
                    "demo_only": True,
                    "fields": fields,
                    "required_document_categories": ["CMC"],
                },
                declaration_en="I confirm that the information supplied is accurate to the best of my knowledge.",
                declaration_ar="أؤكد أن المعلومات المقدمة صحيحة على حد علمي.",
                published=True,
            )

        scenarios = []
        for index, (name_a, name_b, stage) in enumerate(COUPLES, 1):
            a, b = applicant(name_a, index, "M"), applicant(name_b, index + 9, "F")
            closed = stage in ("closed", "appeal")
            manager = members[(index - 1) % len(members)] if index >= 4 else None
            case = m.Case.objects.create(
                id=identity(f"case:{index}"),
                number=f"20261020-{index:02d}",
                origin="synthetic",
                status="closed" if closed else "open",
                closed_at=now if closed else None,
                marriage_date=date(2010 + index, 6, 15),
                spouse_dob_low=a.person.birth_date,
                spouse_dob_high=b.person.birth_date,
                assigned_member=manager,
            )
            proceeding = m.Proceeding.objects.create(
                case=case,
                # The database protects closed proceedings from new revisions.
                # Seed the immutable filings first, then close completed scenarios.
                status="open",
                closed_at=None,
            )
            parties = []
            for slot, owner in (("A", a), ("B", b)):
                party = m.Party.objects.create(
                    case=case,
                    person=owner.person,
                    account=owner,
                    slot=slot,
                    name=f"{owner.first_name} {owner.last_name}",
                    participating=True,
                    reference=f"{case.number}-{owner.first_name[0]}{owner.last_name[0]}{owner.person.birth_date:%Y%m%d}{owner.person.gender}",
                )
                parties.append(party)
                if not closed:
                    m.OpenCaseClaim.objects.create(person=owner.person, case=case)
            app = filing(
                a,
                case,
                proceeding,
                parties[0],
                stage if stage in ("submitted", "returned") else "accepted",
            )
            if index in (4, 6):
                filing(b, case, proceeding, parties[1], "accepted")
            if manager:
                m.CaseAssignment.objects.create(
                    case=case, member=manager, president=president, actor=secretary
                )
                note = m.CaseNote.objects.create(proceeding=proceeding, author=manager)
                m.NoteRevision.objects.create(
                    note=note,
                    number=1,
                    text=f"Case review stage: {stage}. Supporting documents and next steps require review.",
                    actor=manager,
                )
                message = m.Message.objects.create(
                    case=case,
                    sender=manager,
                    body="Your documents have been received for review.",
                )
                m.MessageRecipient.objects.create(message=message, party=parties[0])
                m.Notification.objects.create(
                    recipient=manager,
                    case=case,
                    key=f"{DATASET}:{index}",
                    kind="applicant_changed",
                    payload={"demo_only": True},
                )
            if stage in ("accepted", "investigation", "hearing", "decision", "appeal"):
                agenda = m.AgendaItem.objects.create(
                    session=session,
                    case=case,
                    part=1 if stage == "accepted" else 2,
                    position=index,
                )
                if stage in ("decision", "appeal"):
                    agenda.state = "presented"
                    agenda.save(update_fields=["state"])
                hearing = m.Hearing.objects.create(
                    agenda=agenda, proceeding=proceeding, presenter=manager or secretary
                )
                m.HearingOutcome.objects.create(
                    hearing=hearing,
                    actor=manager or secretary,
                    internal_text="The assigned member reviewed the marriage history and submitted documents with the council.",
                    recommendations="Decision ready for Metropolitan consideration.",
                )
            if stage in ("accepted", "investigation", "hearing", "decision", "appeal"):
                request = m.ReportRequest.objects.create(
                    case=case,
                    proceeding=proceeding,
                    subject=parties[0],
                    author=manager or secretary,
                    title="Marriage circumstances interview",
                    kind="interview",
                    state="completed",
                    questions=[
                        {
                            "code": "DEMO-IDENTITY",
                            "en": "Please confirm your full name.",
                            "ar": "يرجى تأكيد اسمك بالكامل.",
                        }
                    ],
                )
                report = m.Report.objects.create(
                    request=request,
                    author=manager or secretary,
                    identifier=f"{case.number}-REPORT-{timezone.localdate():%Y%m%d}",
                )
                m.ReportRevision.objects.create(
                    report=report,
                    number=1,
                    actor=manager or secretary,
                    answers={"DEMO-IDENTITY": name_a},
                    observations="The applicant confirmed the marriage details. Further clarification of the separation chronology is recommended.",
                )
                if stage == "investigation":
                    old_file = app.attachments.filter(category="MC").first()
                    source(
                        app,
                        "MC",
                        "Updated marriage certificate",
                        version=2,
                        attachment=old_file,
                    )
            if stage in ("decision", "closed", "appeal"):
                denied = stage == "appeal"
                decision = m.DecisionRevision.objects.create(
                    proceeding=proceeding,
                    number=1,
                    type="denied" if denied else "diss-applicant",
                    grounds="Abandonment, subject to the recorded council assessment.",
                    entitlements={
                        str(p.pk): "notice_only"
                        if denied or p.slot == "B"
                        else "certificate"
                        for p in parties
                    },
                    actor=manager,
                )
                for member in members[:3]:
                    m.Vote.objects.create(
                        decision=decision, member=member, actor=member, choice="approve"
                    )
                if closed:
                    m.PresidentialApproval.objects.create(
                        decision=decision, president=president, actor=secretary
                    )
                    source(app, "NOTICE", "Official decision notice")
                    if not denied:
                        certificate = source(
                            app,
                            "DCR",
                            "Decree certificate - unsigned preview",
                        )
                        decree = m.Decree.objects.create(
                            decision=decision,
                            reference=f"DCR-{case.number}",
                            signed_file=certificate,
                            signer=president,
                            issued_at=now,
                        )
                        m.DecreeRelease.objects.create(
                            decree=decree,
                            party=parties[0],
                            actor=secretary,
                            action="release",
                        )
            if stage == "appeal":
                appeal = filing(a, case, proceeding, parties[0], "submitted", "appeal")
                m.AppealSupplement.objects.create(
                    application=appeal,
                    actor=a,
                    text="Newly located supporting correspondence is submitted for consideration.",
                )
            if closed:
                proceeding.status = "closed"
                proceeding.closed_at = now
                proceeding.save(update_fields=["status", "closed_at"])
            m.AuditEvent.objects.create(
                case=case,
                actor=admin,
                action="demo_scenario_loaded",
                source="demo_seed",
                source_id=case.pk,
                metadata={
                    "dataset": DATASET,
                    "stage": stage,
                    "not_real_proceedings": True,
                },
            )
            scenarios.append(
                {
                    "case": case.number,
                    "stage": stage,
                    "applicant": name_a,
                    "spouse": name_b,
                }
            )
        draft_owner = applicant("Thomas Wilson", 20, "M")
        filing(draft_owner, None, None, None, "draft")
        m.CaseNumberCounter.objects.get_or_create(
            date=date(2026, 10, 20), defaults={"last_value": 8}
        )
        ensure_session_agenda(current_session, archived_session)
        added = seed_agenda_cases(current_session)
        enrich_original_cases()
        m.AuditEvent.objects.create(
            actor=admin,
            action="demo_dataset_created",
            source="demo_seed",
            metadata={
                "dataset": DATASET,
                "scenarios": scenarios,
                "no_external_deliveries": True,
            },
        )
        self.stdout.write(
            json.dumps(
                {
                    "dataset": DATASET,
                    "cases": len(COUPLES) + len(added),
                    "agenda_cases": added,
                    "staff_profiles": 9,
                    "scenarios": scenarios,
                    "note": "Synthetic DB snapshots; no emails, payments or real signatures.",
                }
            )
        )
