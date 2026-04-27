# Generated manually for dressifye_saas multi-tenant

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Tenant",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(max_length=200)),
                (
                    "slug",
                    models.SlugField(
                        db_index=True,
                        help_text="URL ve X-Garment-Core-Tenant-Slug header ile eşleme",
                        max_length=120,
                        unique=True,
                    ),
                ),
                (
                    "domain",
                    models.CharField(
                        blank=True,
                        db_index=True,
                        default="",
                        help_text="Özel alan adı (örn. app.musteri.com). Boş = yalnızca slug/header.",
                        max_length=255,
                    ),
                ),
                ("is_active", models.BooleanField(default=True)),
                (
                    "owner_user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="owned_tenants",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Tenant",
                "verbose_name_plural": "Tenantlar",
                "ordering": ["name"],
            },
        ),
    ]
