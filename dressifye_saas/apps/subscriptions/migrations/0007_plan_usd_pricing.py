# Stil Plus $5 / Stil Pro $10 aylık; yıllık ~%16 indirimli yuvarlak tutarlar

from decimal import Decimal

from django.db import migrations


def forwards(apps, schema_editor):
    Plan = apps.get_model("subscriptions", "Plan")
    paid = (
        Plan.objects.filter(is_active=True)
        .exclude(slug="ucretsiz")
        .order_by("order", "pk")
    )
    rows = list(paid[:2])
    if len(rows) >= 1:
        p = rows[0]
        p.price_monthly = Decimal("5.00")
        p.price_yearly = Decimal("50.00")
        p.save(update_fields=["price_monthly", "price_yearly"])
    if len(rows) >= 2:
        p = rows[1]
        p.price_monthly = Decimal("10.00")
        p.price_yearly = Decimal("100.00")
        p.save(update_fields=["price_monthly", "price_yearly"])


def backwards(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("subscriptions", "0006_plan_limits_and_feature_usage"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
