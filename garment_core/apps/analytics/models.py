"""
FAZ 21: Kullanıcı Analitik & Raporlama
"""
from django.db import models
from django.contrib.auth import get_user_model

from apps.core.models import TimeStampedModel

User = get_user_model()


class UsageEvent(TimeStampedModel):
    """Kullanım olayı."""
    EVENT_TYPES = [
        ("tryon", "Try-On"),
        ("stylist", "Stil Asistanı"),
        ("wardrobe_add", "Gardırop Ekleme"),
        ("editor", "Editör"),
        ("makeup", "Makyaj"),
        ("hair", "Saç"),
        ("avatar", "Avatar"),
    ]
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, null=True, blank=True, related_name="usage_events"
    )
    event_type = models.CharField(max_length=30, choices=EVENT_TYPES)
    metadata = models.JSONField(default=dict)
    session_id = models.CharField(max_length=100, blank=True)

    class Meta:
        verbose_name = "Kullanım Olayı"
        verbose_name_plural = "Kullanım Olayları"
        ordering = ["-created_at"]
