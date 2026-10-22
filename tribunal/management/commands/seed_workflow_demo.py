"""Repeatable, isolated workflow snapshots; never an operational data importer."""

import hashlib
import json
import os
import struct
import uuid
import zlib
from datetime import date, timedelta
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.utils import timezone
from tribunal import models as m
from tribunal.services.files import write_private_original

DATASET = "ctm-western-workflow-demo-v1"
ROSTER = [
    ("H.E. Metropolitan", "Serapion", "bishopserapion@lacopts.org", "president"),
    ("Fr. Mauritius", "Mikhail", "frmauritiusmikhail@lacopts.org", "secretary"),
    ("Fr. Youhana", "Ibrahim", "fryouhanaibrahim@lacopts.org", "member"),
    ("Fr. Antony", "Attallah", "frantonyattallah@lacopts.org", "member"),
    ("Fr. Boules", "Mikhail", "frboulesmikhail@lacopts.org", "member"),
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


class Command(BaseCommand):
    help = "Populate an opted-in isolated SQLite review DB with Western-name workflow snapshots."

    @transaction.atomic
    def handle(self, *args, **options):
        if (
            os.environ.get("CTM_SYNTHETIC_DEMO") != "true"
            or os.environ.get("CTM_ENVIRONMENT") != "test"
        ):
            raise CommandError("Explicit isolated synthetic demo environment required.")
        if connection.vendor != "sqlite":
            raise CommandError(
                "This review seed only supports isolated SQLite; no operational database writes."
            )
        if m.Case.objects.exclude(origin="synthetic").exists():
            raise CommandError("Refusing to mix workflow fixtures with non-demo cases.")
        if m.AuditEvent.objects.filter(
            action="demo_dataset_created", metadata__dataset=DATASET
        ).exists():
            self.stdout.write("Dataset already exists; no records or history changed.")
            return
        roster = []
        for first, last, email, role in ROSTER:
            account = m.Account.objects.filter(email__iexact=email).first()
            if account and account.role != role:
                raise CommandError(
                    f"Existing staff role conflict: {email}; no automatic role changes."
                )
            if account is None:
                account = m.Account.objects.create_user(
                    email=email, first_name=first, last_name=last, role=role
                )
            roster.append(account)
        president, secretary = roster[:2]
        admin = roster[-1]
        members = roster[2:8]
        now = timezone.now()
        session, _ = m.CouncilSession.objects.get_or_create(
            date=timezone.localdate() + timedelta(days=7)
        )
        for member in roster[:-1]:
            m.Attendance.objects.create(
                session=session, member=member, actor=admin, present=True
            )
        fields = [
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
                "type": "select",
                "choices": ["M", "F"],
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
        schemas = {}
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

        def applicant(name, index, gender):
            first, last = name.split(" ", 1)
            person = m.Person.objects.create(
                first_name=first,
                last_name=last,
                birth_date=date(1980 + index, 3, 14),
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
            image = category == "PHOTO"
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

        def filing(owner, case, proceeding, party, status, kind="petition"):
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
                "grounds": ["desertion"],
                "statement": "I request council consideration following our separation. We have been living apart since March 2025 despite attempts at reconciliation.",
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
                    for category in ("MC", "CMC", "CDD", "PHOTO")
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
                status="closed" if closed else "open",
                closed_at=now if closed else None,
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
            if stage == "accepted" or stage in ("hearing", "decision", "appeal"):
                agenda = m.AgendaItem.objects.create(
                    session=session,
                    case=case,
                    part=1 if stage == "accepted" else 2,
                    position=index,
                )
                if stage == "decision":
                    agenda.state = "presented"
                    agenda.save(update_fields=["state"])
                    hearing = m.Hearing.objects.create(
                        agenda=agenda, proceeding=proceeding, presenter=manager
                    )
                    m.HearingOutcome.objects.create(
                        hearing=hearing,
                        actor=manager,
                        internal_text="The assigned member reviewed the marriage history and submitted documents with the council.",
                        recommendations="Decision ready for presidential consideration.",
                    )
            if stage in ("investigation", "hearing"):
                request = m.ReportRequest.objects.create(
                    case=case,
                    proceeding=proceeding,
                    subject=parties[0],
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
                )
                report = m.Report.objects.create(
                    request=request,
                    author=manager,
                    identifier=f"{case.number}-REPORT-{timezone.localdate():%Y%m%d}",
                )
                m.ReportRevision.objects.create(
                    report=report,
                    number=1,
                    actor=manager,
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
                    grounds="Desertion / abandonment, subject to the recorded council assessment.",
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
                    "cases": 8,
                    "staff_profiles": 9,
                    "scenarios": scenarios,
                    "note": "Synthetic DB snapshots; no emails, payments or real signatures.",
                }
            )
        )
