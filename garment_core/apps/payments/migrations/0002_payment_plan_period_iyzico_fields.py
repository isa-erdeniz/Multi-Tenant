# Generated manually

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("subscriptions", "0002_plan_order_user_subscription_updates"),
        ("payments", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="payment",
            name="plan",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="subscriptions.plan",
            ),
        ),
        migrations.AddField(
            model_name="payment",
            name="period",
            field=models.CharField(
                choices=[
                    ("monthly", "Aylık"),
                    ("yearly", "Yıllık"),
                ],
                default="monthly",
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name="payment",
            name="iyzico_token",
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AddField(
            model_name="payment",
            name="iyzico_conversation_id",
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AddField(
            model_name="payment",
            name="failure_reason",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="payment",
            name="currency",
            field=models.CharField(default="TRY", max_length=3),
        ),
        migrations.AlterField(
            model_name="payment",
            name="iyzico_payment_id",
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AlterField(
            model_name="payment",
            name="status",
            field=models.CharField(
                choices=[
                    ("pending", "Bekliyor"),
                    ("success", "Başarılı"),
                    ("failed", "Başarısız"),
                    ("refunded", "İade Edildi"),
                ],
                default="pending",
                max_length=20,
            ),
        ),
    ]
