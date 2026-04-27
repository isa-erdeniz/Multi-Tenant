from django.db import models
from django.contrib.auth import get_user_model

from apps.core.models import TenantModel

User = get_user_model()


class TryOnSession(TenantModel):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="tryon_sessions"
    )
    garment = models.ForeignKey(
        "wardrobe.Garment",
        on_delete=models.CASCADE,
        related_name="tryon_sessions",
    )

    user_photo = models.ImageField(upload_to="tryon/input/%Y/%m/", blank=True)
    result_image = models.ImageField(
        upload_to="tryon/output/%Y/%m/", null=True, blank=True
    )

    STATUS_CHOICES = [
        ("pending", "Bekliyor"),
        ("processing", "İşleniyor"),
        ("completed", "Tamamlandı"),
        ("failed", "Başarısız"),
    ]
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="pending"
    )
    error_message = models.TextField(blank=True)
    processing_time = models.FloatField(null=True, blank=True)

    canvas_settings = models.JSONField(null=True, blank=True)

    class Meta:
        verbose_name = "Try-On Oturumu"
        verbose_name_plural = "Try-On Oturumları"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.email} — {self.garment.name} ({self.status})"
