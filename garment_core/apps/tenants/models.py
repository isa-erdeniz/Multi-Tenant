from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel


class Tenant(TimeStampedModel):
    """
    B2C: genelde kullanıcı başına bir kişisel tenant.
    B2B: birden fazla kullanıcı aynı tenant altında paylaşımlı kota kullanır.
    """

    name = models.CharField(max_length=200)
    slug = models.SlugField(
        max_length=120,
        unique=True,
        db_index=True,
        help_text="URL ve X-Garment-Core-Tenant-Slug header ile eşleme",
    )
    domain = models.CharField(
        max_length=255,
        blank=True,
        default="",
        db_index=True,
        help_text="Özel alan adı (örn. app.musteri.com). Boş = yalnızca slug/header.",
    )
    owner_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_tenants",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Tenant"
        verbose_name_plural = "Tenantlar"

    def __str__(self):
        return f"{self.name} ({self.slug})"
