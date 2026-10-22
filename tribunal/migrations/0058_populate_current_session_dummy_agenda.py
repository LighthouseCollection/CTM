from datetime import date

from django.db import migrations


# These are deliberately fictitious, Western-name review records used to make
# both Current-session tabs usable during product review.  They are isolated by
# the `synthetic` origin and can be removed by an administrator like any other
# case record.
CURRENT_SESSION_CASES_TO_ASSIGN = (
    ("20261022-11", "Owen Mitchell", "Lily Mitchell"),
    ("20261022-12", "Ethan Parker", "Grace Parker"),
    ("20261022-13", "Lucas Bennett", "Hannah Bennett"),
    ("20261022-14", "Henry Collins", "Victoria Collins"),
    ("20261022-15", "Jack Morgan", "Natalie Morgan"),
    ("20261022-16", "Samuel Cooper", "Audrey Cooper"),
    ("20261022-17", "Caleb Foster", "Julia Foster"),
    ("20261022-18", "Isaac Turner", "Megan Turner"),
    ("20261022-19", "Dylan Hayes", "Rachel Hayes"),
)

CURRENT_SESSION_HEARINGS = (
    ("20261022-20", "Noah Anderson", "Claire Anderson"),
    ("20261022-21", "Logan Carter", "Ella Carter"),
    ("20261022-22", "Mason Reed", "Avery Reed"),
    ("20261022-23", "Leo Walker", "Sophie Walker"),
    ("20261022-24", "Wyatt Brooks", "Emma Brooks"),
    ("20261022-25", "Julian Scott", "Chloe Scott"),
    ("20261022-26", "Nathan Hughes", "Madison Hughes"),
    ("20261022-27", "Adam Russell", "Olivia Russell"),
    ("20261022-28", "Daniel Price", "Mia Price"),
)


def create_case(apps, *, number, applicant_name, respondent_name, assigned_member=None):
    Case = apps.get_model("tribunal", "Case")
    Person = apps.get_model("tribunal", "Person")
    Party = apps.get_model("tribunal", "Party")
    Proceeding = apps.get_model("tribunal", "Proceeding")

    case, created = Case.objects.get_or_create(
        number=number,
        defaults={
            "status": "open",
            "origin": "synthetic",
            "marriage_date": date(2012, 6, 15),
            "assigned_member": assigned_member,
        },
    )
    if not created:
        return case

    applicant_first, applicant_last = applicant_name.split(" ", 1)
    respondent_first, respondent_last = respondent_name.split(" ", 1)
    applicant = Person.objects.create(
        first_name=applicant_first, last_name=applicant_last, gender="M"
    )
    respondent = Person.objects.create(
        first_name=respondent_first, last_name=respondent_last, gender="F"
    )
    Party.objects.create(case=case, person=applicant, slot="A", name=applicant_name)
    Party.objects.create(case=case, person=respondent, slot="B", name=respondent_name)
    Proceeding.objects.create(case=case, kind="initial", status="open", sequence=1)
    return case


def populate_current_session_dummy_agenda(apps, schema_editor):
    CouncilSession = apps.get_model("tribunal", "CouncilSession")
    AgendaItem = apps.get_model("tribunal", "AgendaItem")
    Account = apps.get_model("tribunal", "Account")

    session = CouncilSession.objects.filter(date=date(2026, 10, 22)).first()
    if session is None:
        return
    presenter = (
        Account.objects.filter(
            is_active=True, role__in=["member", "secretary", "president", "admin"]
        )
        .order_by("email")
        .first()
    )
    if presenter is None:
        return

    next_position = (AgendaItem.objects.filter(session=session).order_by("-position").values_list("position", flat=True).first() or 0) + 1
    for number, applicant_name, respondent_name in CURRENT_SESSION_CASES_TO_ASSIGN:
        case = create_case(
            apps,
            number=number,
            applicant_name=applicant_name,
            respondent_name=respondent_name,
        )
        AgendaItem.objects.get_or_create(
            session=session,
            case=case,
            defaults={"part": 1, "position": next_position, "state": "scheduled"},
        )
        next_position += 1

    for number, applicant_name, respondent_name in CURRENT_SESSION_HEARINGS:
        case = create_case(
            apps,
            number=number,
            applicant_name=applicant_name,
            respondent_name=respondent_name,
            assigned_member=presenter,
        )
        AgendaItem.objects.get_or_create(
            session=session,
            case=case,
            defaults={"part": 2, "position": next_position, "state": "scheduled"},
        )
        next_position += 1


def remove_retired_demo(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    # The original test case must never survive a deployment that contains the
    # administrator purge migration.  The earlier cleanup migration is kept,
    # while this idempotent safeguard reconciles databases where that migration
    # was recorded before the fixture was restored.
    schema_editor.execute("""
        DELETE FROM tribunal_attendance WHERE hearing_id IN (
          SELECT h.id FROM tribunal_hearing h JOIN tribunal_agendaitem a ON a.id=h.agenda_id
          JOIN tribunal_case c ON c.id=a.case_id WHERE c.number='DEMO-HEARING-TEST-20261022');
        DELETE FROM tribunal_hearingoutcome WHERE hearing_id IN (
          SELECT h.id FROM tribunal_hearing h JOIN tribunal_agendaitem a ON a.id=h.agenda_id
          JOIN tribunal_case c ON c.id=a.case_id WHERE c.number='DEMO-HEARING-TEST-20261022');
        DELETE FROM tribunal_hearing WHERE agenda_id IN (
          SELECT a.id FROM tribunal_agendaitem a JOIN tribunal_case c ON c.id=a.case_id WHERE c.number='DEMO-HEARING-TEST-20261022');
        DELETE FROM tribunal_agendaitem WHERE case_id IN (SELECT id FROM tribunal_case WHERE number='DEMO-HEARING-TEST-20261022');
        DELETE FROM tribunal_caseassignment WHERE case_id IN (SELECT id FROM tribunal_case WHERE number='DEMO-HEARING-TEST-20261022');
        DELETE FROM tribunal_auditevent WHERE case_id IN (SELECT id FROM tribunal_case WHERE number='DEMO-HEARING-TEST-20261022');
        DELETE FROM tribunal_notification WHERE case_id IN (SELECT id FROM tribunal_case WHERE number='DEMO-HEARING-TEST-20261022');
        DELETE FROM tribunal_outbox WHERE case_id IN (SELECT id FROM tribunal_case WHERE number='DEMO-HEARING-TEST-20261022');
        DELETE FROM tribunal_party WHERE case_id IN (SELECT id FROM tribunal_case WHERE number='DEMO-HEARING-TEST-20261022');
        DELETE FROM tribunal_proceeding WHERE case_id IN (SELECT id FROM tribunal_case WHERE number='DEMO-HEARING-TEST-20261022');
        DELETE FROM tribunal_case WHERE number='DEMO-HEARING-TEST-20261022';
    """)


class Migration(migrations.Migration):
    dependencies = [("tribunal", "0057_admin_case_purge")]

    operations = [
        migrations.RunPython(remove_retired_demo, migrations.RunPython.noop),
        migrations.RunPython(populate_current_session_dummy_agenda, migrations.RunPython.noop),
    ]
