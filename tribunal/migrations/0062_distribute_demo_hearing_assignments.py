from django.db import migrations


DEMO_HEARING_NUMBERS = tuple(f"20261022-{number:02d}" for number in range(20, 29))


def distribute_demo_hearing_assignments(apps, schema_editor):
    """Rotate the current-session demo hearings across eligible council clergy.

    These fixture-only case numbers are created by migration 0058.  Keeping the
    rotation here prevents the demo agenda from implying that one clergy member
    is responsible for every hearing.
    """
    Account = apps.get_model("tribunal", "Account")
    Case = apps.get_model("tribunal", "Case")

    members = list(
        Account.objects.filter(is_active=True, role__in=["member", "secretary"])
        .order_by("email", "pk")
    )
    if not members:
        return

    for index, number in enumerate(DEMO_HEARING_NUMBERS):
        Case.objects.filter(number=number, origin="synthetic").update(
            assigned_member=members[index % len(members)]
        )


class Migration(migrations.Migration):
    dependencies = [("tribunal", "0061_normalize_demo_session_locations")]

    operations = [
        migrations.RunPython(
            distribute_demo_hearing_assignments, migrations.RunPython.noop
        )
    ]
