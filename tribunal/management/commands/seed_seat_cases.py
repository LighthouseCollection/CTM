"""Top up every council seat holder to five open, fully filled demo cases.

Owner request 2026-11-07: "create 5 cases for each person ... i need these 5
cases to have all data filled out." Fictional data only (the demo_content
generator), clearly marked synthetic, PostgreSQL live-demo only.

- Seat holders are the active staff accounts that hold a council seat
  (public.ctm_council_seat). The president is left out: the app never makes
  the president a case manager (services.council._assign_case).
- Top up only: a holder with fewer than five open assigned cases gets new
  cases with stable numbers DEMO-<HOLDER>-<n>; nothing is moved or duplicated.
- Every new case: both parties' profiles, the full current published petition
  questionnaire answered and checked with the app's own validators, grounds as
  D-0035 codes, generated documents for every required slot with a recorded
  clean scan (test policy, marked as such), an accepted completeness review,
  the assignment record, notes, messages, calls, a priest report request
  (draft, never sent) and a place on the next planned session's agenda.
- Fees are waived by the administrator. No payment is recorded: CTM never
  fakes a payment result.
- Same guards as the other live demo seeders: explicit confirmation, refuse if
  any real case exists, refuse on any council role conflict.
"""
import hashlib
import json
import random
import re
import uuid
from datetime import date, timedelta
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.utils import timezone

from tribunal import models as m
from tribunal.management.commands.seed_workflow_demo import ROSTER, pdf, placeholder_png
from tribunal.management.demo_content import case_story
from tribunal.services.applications import GROUNDS, document_requirements, required_documents, validate_petition
from tribunal.services.council_seats import council_seat
from tribunal.services.files import write_private_original
from tribunal.validation import validate_answers

DATASET = "ctm-seat-cases-demo-v1"
CONFIRM = "FICTITIOUS-DEMO-DATA-ONLY"
TARGET = 5
FIRST_M = ["Aaron", "Blake", "Caleb", "Dylan", "Elliot", "Felix", "Gavin", "Hugo", "Isaac", "Jasper",
           "Kevin", "Lucas", "Miles", "Oliver", "Peter", "Quentin", "Ryan", "Simon", "Tristan", "Victor"]
FIRST_F = ["Abigail", "Bianca", "Clara", "Diana", "Eleanor", "Fiona", "Gemma", "Hazel", "Iris", "Julia",
           "Keira", "Lydia", "Maya", "Nora", "Paige", "Rachel", "Sienna", "Tessa", "Violet", "Zoe"]
LAST = ["Ashford", "Barlow", "Calloway", "Dalton", "Ellison", "Fairbanks", "Garrison", "Holloway",
        "Ingram", "Jennings", "Kendall", "Langley", "Merritt", "Norwood", "Oakley", "Prescott",
        "Radcliffe", "Sheldon", "Thornton", "Whitaker"]
STREETS = ["Maple Dr", "Oak Ave", "Cedar Ln", "Pine St", "Willow Way", "Birch Rd", "Elm Ct", "Aspen Pl"]
TOWNS = [("Bellflower", "90706"), ("Anaheim", "92805"), ("Torrance", "90501"), ("Pasadena", "91101"),
         ("Glendale", "91203"), ("Irvine", "92618"), ("Whittier", "90601"), ("Downey", "90241")]
EDUCATION = ["Bachelor of Science in Nursing", "Bachelor of Arts in Education", "Master of Engineering",
             "Associate Degree in Accounting", "Bachelor of Business Administration"]
OCCUPATIONS = ["Registered Nurse", "Teacher", "Civil Engineer", "Accountant", "Pharmacist", "Sales Manager"]


def slug(account):
    return re.sub(r"[^A-Z0-9]", "", account.email.split("@", 1)[0].upper())[:24] or str(account.pk)[:8]


def seat_holders():
    """Active staff with a council seat; never the president (not a case manager)."""
    holders = []
    for account in m.Account.objects.filter(is_active=True, role__in=("member", "secretary", "admin")):
        if council_seat(account)["seated"]:
            holders.append(account)
    return sorted(holders, key=lambda a: ({"admin": 0, "secretary": 1, "member": 2}[a.role], a.last_name, a.first_name))


def open_count(holder):
    return m.Case.objects.filter(assigned_member=holder, status="open").count()


def field_value(field, ctx, rng):
    """A fictional answer for one questionnaire field (any published version)."""
    code, kind = field["code"], field.get("type", "text")
    if code in ctx:
        return ctx[code]
    if kind == "date":
        return date(2012 + rng.randrange(8), 1 + rng.randrange(12), 1 + rng.randrange(27)).isoformat()
    if kind == "boolean":
        return False
    if kind == "choice":
        choices = [c for c in field.get("choices", []) if str(c).lower() != "unknown"] or field.get("choices", [])
        return choices[rng.randrange(len(choices))] if choices else ""
    if kind == "list":
        if "item_fields" in field:
            row = {"id": str(uuid.UUID(int=rng.getrandbits(128), version=4))}
            for item in field["item_fields"]:
                row[item["code"]] = field_value(item, {}, rng)
            return [row]
        choices = field.get("choices") or []
        return [choices[0]] if choices else []
    label = field.get("label_en") or code.replace("_", " ")
    if kind == "textarea":
        return f"Fictional answer for demonstration: {label}. Provided in full by the applicant."
    return f"Fictional {label}"


def answers_for(questionnaire, ctx, rng):
    answers = {}
    for field in questionnaire.definition.get("fields", []):
        answers[field["code"]] = field_value(field, ctx, rng)
    answers.update(ctx)  # the case's own facts win over generated fillers
    validate_answers(questionnaire, answers)
    validate_petition(answers)
    return answers


class Command(BaseCommand):
    help = "Top up every council seat holder to five open, fully filled fictitious cases (live demo only)."

    def add_arguments(self, parser):
        parser.add_argument("--live-fictitious", action="store_true")
        parser.add_argument("--confirmation", default="")

    @transaction.atomic
    def handle(self, *args, **options):
        if not options["live_fictitious"] or options["confirmation"] != CONFIRM:
            raise CommandError(f"Requires --live-fictitious --confirmation {CONFIRM}.")
        if connection.vendor != "postgresql":
            raise CommandError("The fictitious seat cases require PostgreSQL.")
        if m.Case.objects.exclude(origin__in={"synthetic", "demo"}).exists():
            raise CommandError("Refusing to mix demo cases with non-demo cases.")
        for _first, _last, email, role in ROSTER:
            account = m.Account.objects.filter(email__iexact=email).first()
            if account and account.role != role:
                raise CommandError(f"Existing staff role conflict: {email} is {account.role}, roster says {role}; "
                                   "no automatic role changes.")
        questionnaire = (m.QuestionnaireVersion.objects.filter(purpose="petition", published=True)
                         .order_by("-number").first())
        if questionnaire is None:
            raise CommandError("No published petition questionnaire; run seed_workflow_demo first.")
        president = m.Account.objects.filter(role="president", is_active=True).order_by("created_at").first()
        secretary = m.Account.objects.filter(role="secretary", is_active=True).order_by("created_at").first()
        admin = m.Account.objects.filter(role="admin", is_active=True).order_by("created_at").first()
        if not (president and secretary and admin):
            raise CommandError("An active president, secretary and administrator are required.")
        session = (m.CouncilSession.objects.filter(state__in=("draft", "planned"), date__gte=timezone.localdate())
                   .order_by("date").first())
        self.ctx = {"questionnaire": questionnaire, "president": president, "secretary": secretary,
                    "admin": admin, "session": session, "now": timezone.now()}

        created = []
        for holder in seat_holders():
            have = open_count(holder)
            for n in range(1, TARGET + 1):
                if have >= TARGET:
                    break
                number = f"DEMO-{slug(holder)}-{n:02d}"
                if m.Case.objects.filter(number=number).exists():
                    continue
                self.build_case(holder, number, put_on_agenda=n == 1)
                created.append(number)
                have += 1
        self.stdout.write(json.dumps({"dataset": DATASET, "created": len(created), "cases": created}))
        for holder in seat_holders():
            name = f"{holder.first_name} {holder.last_name}".strip()
            self.stdout.write(f"open cases per seat holder: {name} <{holder.email}> {open_count(holder)}")

    def person_account(self, first, last, gender, birth, key):
        person = m.Person.objects.create(first_name=first, last_name=last, birth_date=birth, gender=gender)
        return m.Account.objects.create_user(
            email=f"{first.lower()}.{last.lower()}.{key}@ctm.example.test", first_name=first, last_name=last,
            person=person, email_verified=True)

    def document(self, app, category, title):
        image = category in {"PHOTO", "SPOUSE_PHOTO"}
        attachment = m.Attachment.objects.create(application=app, case=app.case, proceeding=app.proceeding,
                                                 owner=app.owner, category=category, context="", visibility="own")
        data = placeholder_png() if image else pdf(title, [f"Case: {app.case.number}",
                                                           f"Applicant: {app.owner.first_name} {app.owner.last_name}",
                                                           "Fictional document for demonstration only."])
        extension = "png" if image else "pdf"
        key = f"{DATASET}/{uuid.uuid5(uuid.NAMESPACE_URL, f'{DATASET}:{attachment.pk}')}.{extension}"
        write_private_original(Path(settings.MEDIA_ROOT) / key, data)
        file = m.FileVersion.objects.create(
            attachment=attachment, number=1, object_key=key, original_name=f"{category}.{extension}",
            display_name=f"{app.case.number}-{category}-20261107-0900.{extension}",
            mime_type="image/png" if image else "application/pdf", byte_count=len(data),
            sha256=hashlib.sha256(data).hexdigest(), actor=app.owner, scan_state="clean")
        m.FileTechnicalEvent.objects.create(file=file, task="scan", result="clean", metadata={
            "dataset": DATASET, "test_policy": True, "not_live_antivirus": True})
        return file

    def build_case(self, holder, number, *, put_on_agenda):
        c = self.ctx
        seed = int(hashlib.sha256(number.encode()).hexdigest()[:8], 16)
        rng = random.Random(seed)
        last = LAST[seed % len(LAST)]
        first_a, first_b = FIRST_M[seed % len(FIRST_M)], FIRST_F[(seed // 7) % len(FIRST_F)]
        married = 2006 + seed % 14
        birth_a = date(married - 28 - seed % 5, 1 + seed % 12, 1 + seed % 27)
        birth_b = date(married - 26 - seed % 4, 1 + (seed // 3) % 12, 1 + (seed // 5) % 27)
        key = number.lower()
        a = self.person_account(first_a, last, "M", birth_a, key + "-a")
        b = self.person_account(first_b, last, "F", birth_b, key + "-b")
        marriage = date(married, 1 + seed % 12, 1 + seed % 27)
        separation = date(min(married + 5 + seed % 6, 2025), 1 + (seed // 11) % 12, 1 + seed % 27)
        case = m.Case.objects.create(number=number, origin="synthetic", status="open", marriage_date=marriage,
                                     spouse_dob_low=min(birth_a, birth_b), spouse_dob_high=max(birth_a, birth_b),
                                     assigned_member=holder)
        proceeding = m.Proceeding.objects.create(case=case, status="open")
        party_a = m.Party.objects.create(case=case, person=a.person, account=a, slot="A", name=f"{first_a} {last}",
                                         participating=True, reference=f"{number}-A")
        party_b = m.Party.objects.create(case=case, person=b.person, account=b, slot="B", name=f"{first_b} {last}",
                                         participating=True, reference=f"{number}-B")
        m.OpenCaseClaim.objects.create(person=a.person, case=case)
        m.OpenCaseClaim.objects.create(person=b.person, case=case)

        grounds = sorted(rng.sample(sorted(GROUNDS), 1 + seed % 2))
        story = case_story(seed % 997, party_a.name, first_b, grounds, married)
        town, zipcode = TOWNS[seed % len(TOWNS)]
        town_b, zip_b = TOWNS[(seed // 3) % len(TOWNS)]
        facts = {
            "first_name": first_a, "last_name": last, "birth_date": birth_a.isoformat(), "gender": "M",
            "marriage_date": marriage.isoformat(), "spouse_first_name": first_b, "spouse_last_name": last,
            "spouse_birth_date": birth_b.isoformat(), "spouse_gender": "F", "grounds": grounds,
            "statement": story["statement"], "separation_date": separation.isoformat(),
            "other_names": "None", "birth_country": "Egypt", "nationality": "American",
            "address": f"{100 + seed % 900} {STREETS[seed % len(STREETS)]}, {town}, California, {zipcode}, United States",
            "mobile": f"(562) 555-{1000 + seed % 9000:04d}", "email": a.email,
            "immigration_status": "Citizen", "residing_with": "Alone",
            "education": EDUCATION[seed % len(EDUCATION)], "graduation_year": str(married - 4),
            "occupation": OCCUPATIONS[seed % len(OCCUPATIONS)], "denomination": "Coptic Orthodox",
            "name_of_bishop": "H.E. Metropolitan Serapion", "diocese": "Los Angeles, Southern California and Hawaii",
            "parish_name": f"St. Mary Coptic Orthodox Church, {town}", "father_of_confession": "Fr. Abraam Mikhail",
            "spouse_other_names": "None", "spouse_birth_country": "Egypt", "spouse_nationality": "American",
            "spouse_address": f"{200 + seed % 700} {STREETS[(seed // 5) % len(STREETS)]}, {town_b}, California, {zip_b}, United States",
            "spouse_mobile": f"(714) 555-{1000 + (seed // 7) % 9000:04d}", "spouse_email": b.email,
            "spouse_immigration_status": "Citizen", "spouse_residing_with": "Alone",
            "spouse_education": EDUCATION[(seed // 3) % len(EDUCATION)], "spouse_graduation_year": str(married - 2),
            "spouse_occupation": OCCUPATIONS[(seed // 3) % len(OCCUPATIONS)], "spouse_denomination": "Coptic Orthodox",
            "spouse_name_of_bishop": "H.E. Metropolitan Serapion",
            "spouse_diocese": "Los Angeles, Southern California and Hawaii",
            "spouse_parish_name": f"St. George Coptic Orthodox Church, {town_b}",
            "spouse_father_of_confession": "Fr. Bishoy Hanna",
            "married_outside_coptic_church": "No", "religious_denomination_officiating": "None",
            "date_of_marriage_outside_coptic_church": "None", "church_marriage_date": marriage.isoformat(),
            "officiating_priest": "Fr. Antony Attallah", "church_name": "St. Mark Coptic Orthodox Church",
            "church_location": "Los Angeles, CA", "marriage_diocese": "Diocese of Los Angeles",
            "children": [], "restraining_orders": [],
        }
        q = c["questionnaire"]
        try:
            answers = answers_for(q, facts, rng)
        except ValidationError as exc:
            raise CommandError(f"Generated answers do not satisfy questionnaire v{q.number}: {exc.messages}")
        app = m.Application.objects.create(owner=a, case=case, proceeding=proceeding, party=party_a, kind="petition",
                                           origin="synthetic", status="accepted", current_version=1, questionnaire=q,
                                           submitted_at=c["now"])
        revision = m.AnswerRevision.objects.create(application=app, number=1, actor=a, questionnaire=q, answers=answers)
        m.FeeObligation.objects.create(application=app, status="waived", waived_by=c["admin"])
        files = [self.document(app, category, title) for category, title in (
            ("MC", "Church marriage certificate"), ("CMC", "Civil marriage certificate"),
            ("CDD", "Final civil divorce decree"), ("PHOTO", "Applicant photo"), ("SPOUSE_PHOTO", "Spouse photo"))]
        extra = {x["category"] for x in document_requirements(app, answers)
                 if x["required"]} - {f.attachment.category for f in files}
        files += [self.document(app, category, category) for category in sorted(extra)]
        try:
            required_documents(app, answers)
        except ValidationError as exc:
            raise CommandError(f"Generated documents are incomplete for {number}: {exc.messages}")
        submission = m.Submission.objects.create(
            application=app, revision=revision, actor=a, idempotency_key=f"{DATASET}:{app.pk}",
            manifest=[{"id": str(f.pk), "sha256": f.sha256, "name": f.display_name, "category": f.attachment.category}
                      for f in files],
            attestation={"dataset": DATASET, "demo_only": True, "declaration_en": q.declaration_en})
        m.CompletenessReview.objects.create(submission=submission, actor=c["secretary"], result="accept")
        m.CaseAssignment.objects.create(case=case, member=holder, president=c["president"], actor=c["secretary"])

        start = c["now"] - timedelta(days=40 + seed % 30)
        for step, text in enumerate(story["notes"]):
            at = start + timedelta(days=3 * step + 1)
            note = m.CaseNote.objects.create(proceeding=proceeding, author=holder, created_at=at)
            m.NoteRevision.objects.create(note=note, number=1, text=text, actor=holder, created_at=at)
        for step, (side, body) in enumerate(story["messages"]):
            at = start + timedelta(days=2 * step + 2, hours=9)
            message = m.Message.objects.create(case=case, sender=holder if side == "staff" else a, body=body, created_at=at)
            m.MessageRecipient.objects.create(message=message, party=party_a, read_at=at + timedelta(hours=4))
        for step, (direction, outcome, notes) in enumerate(story["calls"]):
            at = start + timedelta(days=5 * step + 6, hours=14)
            m.CallRecord.objects.create(case=case, party=party_a, actor=holder, occurred_at=at, direction=direction,
                                        outcome=outcome, notes=notes, created_at=at)
        m.ReportRequest.objects.create(
            case=case, proceeding=proceeding, subject=party_a, author=holder, kind="external_priest",
            title=f"Priest report for {party_a.name}", state="draft", external_name="Fr. Abraam Mikhail",
            questions=[{"code": "DEMO-PRIEST-1", "en": "How long have you known the applicant?",
                        "ar": "منذ متى تعرف مقدم الطلب؟"}],
            instructions="Fictional demonstration request; not sent.")
        if put_on_agenda and c["session"] is not None:
            position = (c["session"].agenda.order_by("-position").values_list("position", flat=True).first() or 0) + 1
            m.AgendaItem.objects.create(session=c["session"], case=case, part=2, position=position, state="scheduled")
        m.AuditEvent.objects.create(case=case, actor=c["admin"], action="demo_seat_case_created", source="demo_seed",
                                    source_id=case.pk, metadata={"dataset": DATASET, "not_real_proceeding": True})
        return case
