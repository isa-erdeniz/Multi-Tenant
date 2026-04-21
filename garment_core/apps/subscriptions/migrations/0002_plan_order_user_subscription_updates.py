# Generated manually

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("subscriptions", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="plan",
            name="order",
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.RenameField(
            model_name="usersubscription",
            old_name="iyzico_subscription_id",
            new_name="iyzico_subscription_ref",
        ),
        migrations.AddField(
            model_name="usersubscription",
            name="iyzico_customer_ref",
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AlterField(
            model_name="usersubscription",
            name="user",
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="subscription",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="usersubscription",
            name="status",
            field=models.CharField(
                choices=[
                    ("trial", "Deneme"),
                    ("active", "Aktif"),
                    ("cancelled", "İptal Edildi"),
                    ("expired", "Süresi Doldu"),
                    ("past_due", "Ödeme Gecikti"),
                ],
                default="trial",
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name="plan",
            name="price_monthly",
            field=models.DecimalField(
                decimal_places=2, default=0, max_digits=8
            ),
        ),
        migrations.AlterField(
            model_name="plan",
            name="price_yearly",
            field=models.DecimalField(
                decimal_places=2, default=0, max_digits=8
            ),
        ),
    ]
