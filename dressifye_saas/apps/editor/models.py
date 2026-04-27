"""
FAZ 6: Fotoğraf Düzenleme Modülü — EditSession, EditPreset
"""
from django.db import models
from django.contrib.auth import get_user_model

from apps.core.models import TimeStampedModel

User = get_user_model()


class EditSession(TimeStampedModel):
    """Tek bir düzenleme oturumu."""
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="edit_sessions"
    )
    original_image = models.ImageField(upload_to="editor/original/%Y/%m/")
    edited_image = models.ImageField(
        upload_to="editor/edited/%Y/%m/", null=True, blank=True
    )
    edits_json = models.JSONField(default=dict)  # kırpma, filtre, katman ayarları
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Düzenleme Oturumu"
        verbose_name_plural = "Düzenleme Oturumları"
        ordering = ["-created_at"]


class EditPreset(TimeStampedModel):
    """Kayıtlı düzenleme preset'i."""
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="edit_presets"
    )
    name = models.CharField(max_length=100)
    adjustments_json = models.JSONField(default=dict)
    is_public = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Düzenleme Preseti"
        verbose_name_plural = "Düzenleme Presetleri"
        ordering = ["name"]
