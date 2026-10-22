from django.db import migrations


def replace_presidential_copy(apps, schema_editor):
    HearingOutcome = apps.get_model("tribunal", "HearingOutcome")
    HearingOutcome.objects.filter(recommendations__icontains="presidential").update(
        recommendations="Decision ready for Metropolitan consideration."
    )


class Migration(migrations.Migration):
    dependencies = [("tribunal", "0058_populate_current_session_dummy_agenda")]

    operations = [migrations.RunPython(replace_presidential_copy, migrations.RunPython.noop)]