from django.db import migrations


OLD_EMAIL = "frboulesmikhail@lacopts.org"
NEW_EMAIL = "frpaul@lacopts.org"


def update_demo_boules_login_email(apps, schema_editor):
    Account = apps.get_model("tribunal", "Account")
    if Account.objects.filter(email=NEW_EMAIL).exists():
        return
    Account.objects.filter(
        email=OLD_EMAIL,
        first_name="Fr. Boules",
        last_name="Mikhail",
        is_active=True,
    ).update(email=NEW_EMAIL)


class Migration(migrations.Migration):
    dependencies = [("tribunal", "0062_distribute_demo_hearing_assignments")]

    operations = [migrations.RunPython(update_demo_boules_login_email, migrations.RunPython.noop)]
