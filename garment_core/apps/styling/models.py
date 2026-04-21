from django.db import models
from django.contrib.auth import get_user_model

from apps.core.models import TenantModel

User = get_user_model()


class StyleSession(TenantModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="style_sessions")
    title = models.CharField(max_length=200, blank=True)

    # Kullanıcının isteği
    user_prompt = models.TextField()

    # Bağlam — hava durumu, etkinlik, ruh hali vs.
    context = models.JSONField(default=dict, blank=True)

    # MEHLR'den gelen yanıt (ham metin)
    ai_response = models.TextField(blank=True)

    # Önerilen kıyafet kombinasyonu (JSON)
    suggested_outfit = models.JSONField(null=True, blank=True)

    # Önerilen kıyafetler (M2M)
    garments_suggested = models.ManyToManyField(
        "wardrobe.Garment", blank=True, related_name="style_sessions"
    )

    STATUS_CHOICES = [
        ("pending", "Bekliyor"),
        ("processing", "İşleniyor"),
        ("completed", "Tamamlandı"),
        ("failed", "Başarısız"),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    processing_time = models.FloatField(null=True, blank=True)
    error_message = models.TextField(blank=True)

    # Kullanıcı bu öneriyi beğendi mi?
    is_saved = models.BooleanField(default=False)
    user_rating = models.PositiveSmallIntegerField(null=True, blank=True)  # 1-5

    class Meta:
        verbose_name = "Stil Oturumu"
        verbose_name_plural = "Stil Oturumları"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.email} — {self.title or self.user_prompt[:40]}"

    def get_title(self):
        return self.title or self.user_prompt[:60]
