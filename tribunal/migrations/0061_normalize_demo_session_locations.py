from django.db import migrations


DEMO_SESSION_LOCATIONS = [
    "St. Mark Coptic Orthodox Church, Los Angeles, California",
    "St. Mary Coptic Orthodox Church, Los Angeles, California",
]
CANONICAL_DEMO_LOCATION = "St. George Coptic Orthodox Church, Bellflower, California"


def normalize_demo_session_locations(apps, schema_editor):
    CouncilSession = apps.get_model("tribunal", "CouncilSession")
    CouncilSession.objects.filter(
        location__in=DEMO_SESSION_LOCATIONS, state__in=["draft", "planned"]
    ).update(
        location=CANONICAL_DEMO_LOCATION
    )


class Migration(migrations.Migration):
    dependencies = [("tribunal", "0060_reassign_president_case_managers")]

    operations = [migrations.RunPython(normalize_demo_session_locations, migrations.RunPython.noop)]
