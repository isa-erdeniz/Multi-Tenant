# Stil Plus / Stil Pro görünen adları ve güncel fiyatlar (ilk iki ücretli plan)

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
        p.name = "Stil Plus"
        p.price_monthly = Decimal("99.00")
        p.price_yearly = Decimal("999.00")
        p.save(update_fields=["name", "price_monthly", "price_yearly"])
    if len(rows) >= 2:
        p = rows[1]
        p.name = "Stil Pro"
        p.price_monthly = Decimal("199.00")
        p.price_yearly = Decimal("1999.00")
        p.save(update_fields=["name", "price_monthly", "price_yearly"])


def backwards(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("subscriptions", "0004_usagequota"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
