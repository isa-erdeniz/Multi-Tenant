"""
FAZ 8: AR Makyaj Deneme Motoru — MakeupLook, MakeupProduct, MakeupSession
"""
from django.db import models
from django.contrib.auth import get_user_model

from apps.core.models import TimeStampedModel

User = get_user_model()


class MakeupLook(TimeStampedModel):
    """Hazır makyaj görünümü (200+ one-tap looks)."""
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=50)  # günlük, gece, düğün, vb.
    thumbnail = models.ImageField(upload_to="beauty/looks/%Y/%m/", null=True, blank=True)
    products_json = models.JSONField(default=list)  # [{type, color_hex, opacity}, ...]
    is_premium = models.BooleanField(default=False)
    creator = models.CharField(max_length=100, blank=True)

    class Meta:
        verbose_name = "Makyaj Görünümü"
        verbose_name_plural = "Makyaj Görünümleri"
        ordering = ["name"]


class MakeupProduct(TimeStampedModel):
    """Makyaj ürünü tanımı."""
    PRODUCT_TYPES = [
        ("lipstick", "Ruj"),
        ("eyeshadow", "Far"),
        ("blush", "Allık"),
        ("foundation", "Fondöten"),
        ("eyeliner", "Eyeliner"),
        ("mascara", "Rimel"),
        ("brow", "Kaş"),
    ]
    product_type = models.CharField(max_length=20, choices=PRODUCT_TYPES)
    color_hex = models.CharField(max_length=7, default="#000000")
    opacity = models.FloatField(default=1.0)
    brand = models.CharField(max_length=100, blank=True)

    class Meta:
        verbose_name = "Makyaj Ürünü"
        verbose_name_plural = "Makyaj Ürünleri"


class MakeupSession(TimeStampedModel):
    """Kullanıcı makyaj deneme oturumu."""
    STATUS_CHOICES = [
        ("pending", "Bekliyor"),
        ("processing", "İşleniyor"),
        ("completed", "Tamamlandı"),
        ("failed", "Hata"),
    ]

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="makeup_sessions"
    )
    input_image = models.ImageField(upload_to="beauty/input/%Y/%m/", null=True, blank=True)
    applied_look = models.ForeignKey(
        MakeupLook, on_delete=models.SET_NULL, null=True, blank=True
    )
    result_image = models.ImageField(
        upload_to="beauty/output/%Y/%m/", null=True, blank=True
    )
    products_json = models.JSONField(default=list)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    output_data = models.JSONField(default=dict)

    class Meta:
        verbose_name = "Makyaj Oturumu"
        verbose_name_plural = "Makyaj Oturumları"
        ordering = ["-created_at"]
