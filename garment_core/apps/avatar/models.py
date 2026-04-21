"""
FAZ 10: AI Avatar & Dijital Kimlik Oluşturma
"""
from django.db import models
from django.contrib.auth import get_user_model

from apps.core.models import TimeStampedModel

User = get_user_model()


class AvatarStyle(TimeStampedModel):
    """Avatar stili (gerçekçi, anime, karikatür, vb.)."""
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=50)
    example_images = models.JSONField(default=list)
    prompt_template = models.TextField(blank=True)
    is_premium = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Avatar Stili"
        verbose_name_plural = "Avatar Stilleri"
        ordering = ["name"]


class AvatarSession(TimeStampedModel):
    """AI avatar oluşturma oturumu."""
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="avatar_sessions"
    )
    input_selfie = models.ImageField(upload_to="avatar/input/%Y/%m/")
    style = models.ForeignKey(
        AvatarStyle, on_delete=models.SET_NULL, null=True, blank=True
    )
    result_images = models.JSONField(default=list)  # [url1, url2, ...]

    class Meta:
        verbose_name = "Avatar Oturumu"
        verbose_name_plural = "Avatar Oturumları"
        ordering = ["-created_at"]


class BackgroundTemplate(TimeStampedModel):
    """Arka plan şablonu (Around the World)."""
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=50)
    image = models.ImageField(upload_to="avatar/backgrounds/%Y/%m/")
    location_name = models.CharField(max_length=100, blank=True)

    class Meta:
        verbose_name = "Arka Plan Şablonu"
        verbose_name_plural = "Arka Plan Şablonları"
