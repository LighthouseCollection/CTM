# Consolidates the independently developed production migration heads.
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("tribunal", "0044_call_record_direction"),
        ("tribunal", "0051_runtime_settings_consumers"),
        ("tribunal", "0052_external_recording_completion"),
    ]

    operations = []
