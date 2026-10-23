from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("tribunal", "0042_merge_account_administration_and_session_workspace")]

    operations = [
        migrations.AddField(
            model_name="councilsession",
            name="adjourned_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
