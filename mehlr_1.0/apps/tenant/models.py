from __future__ import annotations

from typing import Any

from django.db import models


class Tenant(models.Model):
    """Railway üzerinde tek backend; domain ile marka / AI / veri rolü ayrımı."""

    class DataType(models.TextChoices):
        HAIR = "hair", "Saç/Sağlık"
        STYLE_BASIC = "style_basic", "Temel Stil"
        FASHION = "fashion", "Tam Moda"
        MASTER = "master", "Merkez/Hepsi"

    name: str = models.CharField(max_length=100)
    domain: str = models.CharField(max_length=255, unique=True, db_index=True)
    slug: str = models.SlugField(unique=True, db_index=True)

    data_type: str = models.CharField(
        max_length=20,
        choices=DataType.choices,
        default=DataType.MASTER,
        db_index=True,
    )
    sync_to_tenant: Tenant | None = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="sync_sources",
    )

    logo_url: str = models.URLField(blank=True)
    primary_color: str = models.CharField(max_length=7, default="#c9a84c")
    favicon: str = models.URLField(blank=True)

    features: dict[str, Any] = models.JSONField(default=dict, blank=True)

    ai_prompt_prefix: str = models.TextField(blank=True)
    ai_temperature: float = models.FloatField(default=0.7)

    is_active: bool = models.BooleanField(default=True)
    created_at: models.DateTimeField = models.DateTimeField(auto_now_add=True)
    updated_at: models.DateTimeField = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Tenant"
        verbose_name_plural = "Tenantlar"

    def __str__(self) -> str:
        return f"{self.name} ({self.domain})"


class CrossTenantData(models.Model):
    """Kaynak tenant’tan hedefe (çoğunlukla dressifye) akan veri birleştirme kaydı."""

    source_tenant: Tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name="sent_data",
    )
    target_tenant: Tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name="received_data",
    )
    user_external_id: str = models.CharField(max_length=255, db_index=True)
    data_type: str = models.CharField(max_length=50, db_index=True)
    data_payload: dict[str, Any] = models.JSONField(default=dict, blank=True)
    synced_at: models.DateTimeField = models.DateTimeField(auto_now_add=True)
    is_processed: bool = models.BooleanField(default=False)

    class Meta:
        ordering = ["-synced_at"]
        verbose_name = "Çapraz tenant verisi"
        verbose_name_plural = "Çapraz tenant verileri"
        indexes = [
            models.Index(fields=["user_external_id", "data_type"]),
        ]

    def __str__(self) -> str:
        return f"{self.source_tenant.slug}→{self.target_tenant.slug} ({self.user_external_id})"
