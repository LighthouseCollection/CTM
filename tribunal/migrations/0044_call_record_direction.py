from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("tribunal", "0043_session_adjournment")]

    operations = [
        migrations.AddField(
            model_name="callrecord",
            name="direction",
            field=models.CharField(default="sent", max_length=10),
        ),
    ]
