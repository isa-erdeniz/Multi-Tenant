import django.db.models.deletion
from django.db import migrations, models


def backfill_payment_tenant(apps, schema_editor):
    Payment = apps.get_model("payments", "Payment")
    User = apps.get_model("accounts", "DressifyeUser")
    for p in Payment.objects.filter(tenant_id__isnull=True).iterator():
        tid = (
            User.objects.filter(pk=p.user_id)
            .values_list("tenant_id", flat=True)
            .first()
        )
        if tid:
            Payment.objects.filter(pk=p.pk).update(tenant_id=tid)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("payments", "0004_webhook_event_idempotency"),
        ("accounts", "0002_dressifyeuser_tenant"),
    ]

    operations = [
        migrations.AddField(
            model_name="payment",
            name="tenant",
            field=models.ForeignKey(
                help_text="Ödeme anındaki tenant; callback'te kullanıcı ile doğrulanır.",
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="payments",
                to="tenants.tenant",
            ),
        ),
        migrations.RunPython(backfill_payment_tenant, noop),
        migrations.AlterField(
            model_name="payment",
            name="tenant",
            field=models.ForeignKey(
                help_text="Ödeme anındaki tenant; callback'te kullanıcı ile doğrulanır.",
                on_delete=django.db.models.deletion.CASCADE,
                related_name="payments",
                to="tenants.tenant",
            ),
        ),
    ]
