from django.db import migrations


def populate_archived_session_data(apps, schema_editor):
    CouncilSession = apps.get_model("tribunal", "CouncilSession")
    Case = apps.get_model("tribunal", "Case")
    AgendaItem = apps.get_model("tribunal", "AgendaItem")
    Hearing = apps.get_model("tribunal", "Hearing")
    HearingOutcome = apps.get_model("tribunal", "HearingOutcome")
    Account = apps.get_model("tribunal", "Account")

    cases = list(Case.objects.exclude(number="DEMO-HEARING-TEST-20261022").order_by("number"))
    part_one, part_two = cases[:5], cases[5:10]
    presenter = Account.objects.filter(is_active=True, role__in=["member", "secretary", "president"]).order_by("email").first()
    if len(part_one) < 5 or len(part_two) < 5 or presenter is None:
        return
    for session in CouncilSession.objects.filter(state="closed").order_by("date"):
        for position, case in enumerate(part_one, start=1):
            AgendaItem.objects.get_or_create(
                session=session, case=case,
                defaults={"part": 1, "position": position, "state": "scheduled"},
            )
        for position, case in enumerate(part_two, start=1):
            item, _ = AgendaItem.objects.get_or_create(
                session=session, case=case,
                defaults={"part": 2, "position": position, "state": "heard"},
            )
            hearing, _ = Hearing.objects.get_or_create(
                agenda=item,
                defaults={"state": "heard", "presenter": case.assigned_member or presenter,
                          "proceeding": case.proceedings.order_by("sequence").first()},
            )
            HearingOutcome.objects.get_or_create(
                hearing=hearing,
                defaults={"internal_text": "Fictitious archived hearing record.",
                          "recommendations": "Fictitious recommendation recorded for tribunal workflow review.",
                          "actor": case.assigned_member or presenter},
            )


class Migration(migrations.Migration):
    dependencies = [("tribunal", "0055_draft_session_delete")]
    operations = [migrations.RunPython(populate_archived_session_data, migrations.RunPython.noop)]
