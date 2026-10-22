from django.db import migrations


class Migration(migrations.Migration):
    """Hearing outcomes are immutable; council projections normalize retired display wording."""

    dependencies = [("tribunal", "0058_populate_current_session_dummy_agenda")]

    operations = [migrations.RunPython(migrations.RunPython.noop, migrations.RunPython.noop)]
