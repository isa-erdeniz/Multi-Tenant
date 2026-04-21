"""
FAZ 9: Sanal Saç Değiştirme & Renklendirme
"""
from django.db import models
from django.contrib.auth import get_user_model

from apps.core.models import TimeStampedModel

User = get_user_model()


class HairStyle(TimeStampedModel):
    """Saç stili/modeli."""
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=50)  # bob, pixie, lob, vb.
    gender = models.CharField(max_length=20, blank=True)  # kadın, erkek, unisex
    thumbnail = models.ImageField(upload_to="hair/styles/%Y/%m/", null=True, blank=True)
    overlay_data = models.JSONField(null=True, blank=True)
    is_premium = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Saç Stili"
        verbose_name_plural = "Saç Stilleri"
        ordering = ["name"]


class HairColor(TimeStampedModel):
    """Saç rengi."""
    name = models.CharField(max_length=50)
    hex_code = models.CharField(max_length=7)
    category = models.CharField(max_length=20)  # doğal, fantezi, ombre
    preview_image = models.ImageField(
        upload_to="hair/colors/%Y/%m/", null=True, blank=True
    )

    class Meta:
        verbose_name = "Saç Rengi"
        verbose_name_plural = "Saç Renkleri"
        ordering = ["name"]


class HairSession(TimeStampedModel):
    """Saç değiştirme oturumu."""
    STATUS_CHOICES = [
        ("pending", "Bekliyor"),
        ("processing", "İşleniyor"),
        ("completed", "Tamamlandı"),
        ("failed", "Hata"),
    ]

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="hair_sessions"
    )
    input_image = models.ImageField(upload_to="hair/input/%Y/%m/", null=True, blank=True)
    applied_style = models.ForeignKey(
        HairStyle, on_delete=models.SET_NULL, null=True, blank=True
    )
    applied_color = models.ForeignKey(
        HairColor, on_delete=models.SET_NULL, null=True, blank=True
    )
    result_image = models.ImageField(
        upload_to="hair/output/%Y/%m/", null=True, blank=True
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    output_data = models.JSONField(default=dict)

    class Meta:
        verbose_name = "Saç Oturumu"
        verbose_name_plural = "Saç Oturumları"
        ordering = ["-created_at"]
