"""
FAZ 11: Hazır Görünüm Paketleri & Tek Dokunuş Stiller
"""
from django.db import models
from django.contrib.auth import get_user_model

from apps.core.models import TimeStampedModel

User = get_user_model()


class LookPackage(TimeStampedModel):
    """Tek dokunuşla komple görünüm paketi."""
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=50)
    creator = models.CharField(max_length=100, blank=True)
    thumbnail = models.ImageField(upload_to="looks/%Y/%m/", null=True, blank=True)
    components_json = models.JSONField(default=dict)  # makyaj + saç + kıyafet
    is_premium = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Görünüm Paketi"
        verbose_name_plural = "Görünüm Paketleri"
        ordering = ["name"]


class LookRating(TimeStampedModel):
    """Görünüm puanlama."""
    look = models.ForeignKey(
        LookPackage, on_delete=models.CASCADE, related_name="ratings"
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="look_ratings"
    )
    score = models.PositiveSmallIntegerField()  # 1-5
    review_text = models.TextField(blank=True)

    class Meta:
        verbose_name = "Görünüm Puanı"
        verbose_name_plural = "Görünüm Puanları"
        unique_together = ["look", "user"]
