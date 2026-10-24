"""Fill the council review queue with clearly marked fictitious filings."""

from datetime import date

from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.utils import timezone

from tribunal import models as m


DATASET = "ctm-new-applications-demo-v1"
COUPLES = [
    ("Noah", "Anderson", "Claire", "Anderson"),
    ("Logan", "Carter", "Ella", "Carter"),
    ("Mason", "Reed", "Avery", "Reed"),
    ("Leo", "Walker", "Sophie", "Walker"),
    ("Wyatt", "Brooks", "Emma", "Brooks"),
    ("Julian", "Scott", "Chloe", "Scott"),
    ("Nathan", "Hughes", "Madison", "Hughes"),
    ("Adam", "Russell", "Olivia", "Russell"),
    ("Daniel", "Price", "Mia", "Price"),
]


class Command(BaseCommand):
    help = "Fill the council New Applications queue with explicitly opted-in fictitious filings."

    def add_arguments(self, parser):
        parser.add_argument("--live-fictitious", action="store_true")
        parser.add_argument("--confirmation", default="")

    @transaction.atomic
    def handle(self, *args, **options):
        if not options["live_fictitious"] or options["confirmation"] != "FICTITIOUS-DEMO-DATA-ONLY":
            raise CommandError("Requires --live-fictitious --confirmation FICTITIOUS-DEMO-DATA-ONLY.")
        if connection.vendor != "postgresql":
            raise CommandError("The fictitious live queue requires PostgreSQL.")
        if m.Case.objects.exclude(origin__in={"synthetic", "demo"}).exists():
            raise CommandError("Refusing to mix demo queue rows with non-demo cases.")

        existing = m.Application.objects.filter(kind="petition", status="submitted").exclude(origin="closed_case_intake").count()
        needed = max(0, 10 - existing)
        if not needed:
            self.stdout.write(self.style.SUCCESS("New Applications already contains at least 10 submitted filings."))
            return
        questionnaire = m.QuestionnaireVersion.objects.filter(purpose="petition", published=True).order_by("-number").first()
        if questionnaire is None:
            questionnaire = m.QuestionnaireVersion.objects.create(purpose="petition", number=1, published=True, definition={"dataset": DATASET, "demo_only": True, "fields": []}, declaration_en="Synthetic demonstration filing.")
        staff = m.Account.objects.filter(role__in={"admin", "secretary"}).order_by("created_at").first()
        if staff is None:
            raise CommandError("A council administrator or secretary is required.")

        created = []
        for offset, (a_first, a_last, b_first, b_last) in enumerate(COUPLES):
            if len(created) >= needed:
                break
            email = f"{a_first.lower()}.{a_last.lower()}.new-app@ctm.example.test"
            if m.Account.objects.filter(email=email).exists():
                continue
            applicant = m.Account.objects.create_user(email=email, first_name=a_first, last_name=a_last, email_verified=True, person=m.Person.objects.create(first_name=a_first, last_name=a_last, birth_date=date(1981 + offset, 3, 14), gender="M"))
            respondent = m.Account.objects.create_user(email=f"{b_first.lower()}.{b_last.lower()}.new-respondent@ctm.example.test", first_name=b_first, last_name=b_last, email_verified=True, person=m.Person.objects.create(first_name=b_first, last_name=b_last, birth_date=date(1984 + offset, 8, 22), gender="F"))
            number = f"DEMO-NEW-{offset + 1:02d}"
            case = m.Case.objects.create(number=number, origin="synthetic", status="open", marriage_date=date(2010 + offset, 6, 15))
            proceeding = m.Proceeding.objects.create(case=case, status="open")
            party = m.Party.objects.create(case=case, person=applicant.person, account=applicant, slot="A", name=f"{a_first} {a_last}", participating=True, reference=f"{number}-A")
            m.Party.objects.create(case=case, person=respondent.person, account=respondent, slot="B", name=f"{b_first} {b_last}", participating=True, reference=f"{number}-B")
            m.OpenCaseClaim.objects.create(person=applicant.person, case=case)
            m.OpenCaseClaim.objects.create(person=respondent.person, case=case)
            app = m.Application.objects.create(owner=applicant, case=case, proceeding=proceeding, party=party, kind="petition", origin="synthetic", status="submitted", current_version=1, questionnaire=questionnaire, submitted_at=timezone.now())
            revision = m.AnswerRevision.objects.create(application=app, number=1, actor=applicant, questionnaire=questionnaire, answers={"first_name": a_first, "last_name": a_last, "gender": "M", "marriage_date": case.marriage_date.isoformat(), "statement": "Fictitious submission for CTM interface review only."})
            m.FeeObligation.objects.create(application=app, status="waived", waived_by=staff)
            m.Submission.objects.create(application=app, revision=revision, actor=applicant, idempotency_key=f"{DATASET}:{app.pk}", manifest=[], attestation={"dataset": DATASET, "demo_only": True})
            m.AuditEvent.objects.create(case=case, actor=staff, action="demo_new_application_created", source="demo_seed", source_id=app.pk, metadata={"dataset": DATASET, "not_real_proceeding": True})
            created.append(number)
        self.stdout.write(self.style.SUCCESS(f"Created {len(created)} fictitious submitted applications: {', '.join(created)}"))
