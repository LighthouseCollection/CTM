from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("tribunal", "0013_decision_privacy")]
    operations = [
        migrations.AddField(model_name="checkoutintent", name="payment_reference",
            field=models.CharField(max_length=250, blank=True, default="", db_index=True)),
        migrations.AddField(model_name="paymentevent", name="payment_reference",
            field=models.CharField(max_length=250, blank=True, default="", db_index=True)),
    ]
