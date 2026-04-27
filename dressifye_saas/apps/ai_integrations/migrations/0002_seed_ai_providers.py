# Generated manually — varsayılan sağlayıcı satırları (anahtarlar boş).

from django.db import migrations


def seed_providers(apps, schema_editor):
    AIProvider = apps.get_model("ai_integrations", "AIProvider")
    rows = [
        ("wearview", "https://api.wearview.com/v1"),
        ("zmo", "https://api.zmo.ai/v1"),
        ("style3d", "https://api.style3d.com/v1"),
    ]
    for name, url in rows:
        AIProvider.objects.get_or_create(
            name=name,
            defaults={
                "base_url": url,
                "is_active": True,
                "rate_limit_per_minute": 60,
            },
        )


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("ai_integrations", "0001_ai_integrations_and_plan_credits"),
    ]

    operations = [
        migrations.RunPython(seed_providers, noop),
    ]
