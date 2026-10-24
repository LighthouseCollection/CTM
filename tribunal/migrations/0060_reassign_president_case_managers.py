from django.db import migrations


def reassign_president_case_managers(apps, schema_editor):
    Account = apps.get_model("tribunal", "Account")
    Case = apps.get_model("tribunal", "Case")

    replacement = (
        Account.objects.filter(is_active=True, role__in=["member", "secretary"])
        .order_by("email", "pk")
        .first()
    )
    if replacement is not None:
        Case.objects.filter(assigned_member__role="president").update(
            assigned_member=replacement
        )


class Migration(migrations.Migration):
    dependencies = [("tribunal", "0059_replace_presidential_copy")]

    operations = [migrations.RunPython(reassign_president_case_managers, migrations.RunPython.noop)]
