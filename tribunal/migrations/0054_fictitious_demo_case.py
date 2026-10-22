from django.db import migrations
from django.utils import timezone


DEMO_CASE = "DEMO-HEARING-TEST-20261022"
DEMO_ACCOUNTS = (
    ("A", "demo.applicant@ctm.example.invalid", "Demo", "Applicant", "M"),
    ("B", "demo.respondent@ctm.example.invalid", "Demo", "Respondent", "F"),
)


def seed_fictitious_demo_case(apps, schema_editor):
    Case = apps.get_model("tribunal", "Case")
    Party = apps.get_model("tribunal", "Party")
    Person = apps.get_model("tribunal", "Person")
    Account = apps.get_model("tribunal", "Account")
    Proceeding = apps.get_model("tribunal", "Proceeding")
    QuestionnaireVersion = apps.get_model("tribunal", "QuestionnaireVersion")
    Application = apps.get_model("tribunal", "Application")
    AnswerRevision = apps.get_model("tribunal", "AnswerRevision")
    Submission = apps.get_model("tribunal", "Submission")
    FeeObligation = apps.get_model("tribunal", "FeeObligation")

    case = Case.objects.filter(number=DEMO_CASE).first()
    if case is None:
        return
    parties = {party.slot: party for party in Party.objects.filter(case=case)}
    linked = {}
    for slot, email, first_name, last_name, gender in DEMO_ACCOUNTS:
        party = parties.get(slot)
        if party is None:
            continue
        account = Account.objects.filter(email=email).first()
        if account is None:
            person = Person.objects.create(
                first_name=first_name, last_name=last_name, gender=gender
            )
            account = Account.objects.create(
                email=email,
                first_name=first_name,
                last_name=last_name,
                person=person,
                role="applicant",
                is_active=True,
                email_verified=True,
                password="!",
            )
        party.account = account
        party.person = account.person
        party.save(update_fields=["account", "person"])
        linked[slot] = (party, account)

    applicant = linked.get("A")
    if applicant is None or Application.objects.filter(case=case, kind="petition").exists():
        return
    proceeding = Proceeding.objects.filter(case=case, status="open").order_by("sequence").first()
    questionnaire = QuestionnaireVersion.objects.filter(
        purpose="petition", published=True
    ).order_by("-number").first()
    if proceeding is None or questionnaire is None:
        return
    party, account = applicant
    submitted_at = timezone.now()
    application = Application.objects.create(
        owner=account,
        case=case,
        proceeding=proceeding,
        party=party,
        kind="petition",
        origin="portal",
        status="submitted",
        current_version=1,
        questionnaire=questionnaire,
        submitted_at=submitted_at,
        last_activity=submitted_at,
    )
    revision = AnswerRevision.objects.create(
        application=application,
        number=1,
        actor=account,
        questionnaire=questionnaire,
        answers={
            "first_name": "Demo",
            "last_name": "Applicant",
            "gender": "M",
            "grounds": ["desertion"],
            "statement": "FICTITIOUS DEMO ONLY — submitted petition for live interface testing.",
        },
    )
    Submission.objects.create(
        application=application,
        revision=revision,
        actor=account,
        idempotency_key=f"fictitious-demo-petition:{application.pk}",
        manifest=[],
        attestation={"demo_only": True, "fictitious": True},
    )
    FeeObligation.objects.create(
        application=application, amount_minor=25000, currency="USD", status="waived"
    )


class Migration(migrations.Migration):
    dependencies = [("tribunal", "0053_merge_all_feature_branches")]

    operations = [migrations.RunPython(seed_fictitious_demo_case, migrations.RunPython.noop)]
