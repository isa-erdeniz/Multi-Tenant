"""
mehlr_1.0 — Veritabanı modelleri.
ErdenizTech AI Engine için Project, Conversation, Message, AnalysisReport, ModuleRegistry,
Dressifye senkronizasyonu için DressifyeUser, DressifyeGarment, OutfitRecommendation.
"""
from __future__ import annotations

from typing import Any

from django.conf import settings
from django.db import models


class Project(models.Model):
    """ErdenizTech bünyesindeki projeleri temsil eder."""
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField()
    project_type = models.CharField(max_length=50)
    context_prompt = models.TextField()
    data_schema = models.JSONField(default=dict)
    api_endpoint = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Proje'
        verbose_name_plural = 'Projeler'

    def __str__(self):
        return self.name


class Conversation(models.Model):
    """Kullanıcı ile MEHLR arasındaki sohbet oturumu."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='mehlr_conversations',
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='conversations',
    )
    title = models.CharField(max_length=200, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        verbose_name = 'Sohbet'
        verbose_name_plural = 'Sohbetler'

    def __str__(self):
        return self.title or f"Sohbet #{self.pk}"


class Message(models.Model):
    """Sohbetteki her bir mesaj."""
    class Role(models.TextChoices):
        USER = 'user', 'Kullanıcı'
        ASSISTANT = 'assistant', 'MEHLR'
        SYSTEM = 'system', 'Sistem'

    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='messages',
    )
    role = models.CharField(max_length=10, choices=Role.choices)
    content = models.TextField()
    tokens_used = models.IntegerField(default=0)
    processing_time = models.FloatField(default=0.0)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        verbose_name = 'Mesaj'
        verbose_name_plural = 'Mesajlar'

    def __str__(self):
        return f"{self.role}: {self.content[:50]}..."


class AnalysisReport(models.Model):
    """MEHLR'in ürettiği analiz raporları."""
    class ReportType(models.TextChoices):
        DAILY = 'daily', 'Günlük'
        WEEKLY = 'weekly', 'Haftalık'
        MONTHLY = 'monthly', 'Aylık'
        CUSTOM = 'custom', 'Özel'

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='reports',
    )
    report_type = models.CharField(max_length=10, choices=ReportType.choices)
    title = models.CharField(max_length=200)
    content = models.TextField()
    data_snapshot = models.JSONField(default=dict)
    generated_by = models.ForeignKey(
        Conversation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='generated_reports',
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Analiz Raporu'
        verbose_name_plural = 'Analiz Raporları'

    def __str__(self):
        return self.title


class ModuleRegistry(models.Model):
    """Yüklenmiş MEHLR modüllerinin kaydı."""
    name = models.CharField(max_length=100, unique=True)
    module_path = models.CharField(max_length=200)
    version = models.CharField(max_length=20)
    supported_projects = models.ManyToManyField(Project, blank=True, related_name='modules')
    is_enabled = models.BooleanField(default=True)
    config = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Modül Kaydı'
        verbose_name_plural = 'Modül Kayıtları'

    def __str__(self):
        return f"{self.name} v{self.version}"


# ─────────────────────────────────────────────
# Dressifye — shadow / senkronizasyon modelleri
# ─────────────────────────────────────────────


class DressifyeUser(models.Model):
    """Dressifye kullanıcısının MEHLR tarafındaki gölge kaydı (senkronizasyon / cache)."""

    external_id: str = models.CharField(max_length=255, unique=True, db_index=True)
    username: str = models.CharField(max_length=150)
    profile_data: dict[str, Any] = models.JSONField(default=dict, blank=True)
    last_synced: models.DateTimeField | None = models.DateTimeField(null=True, blank=True)
    created_at: models.DateTimeField = models.DateTimeField(auto_now_add=True)
    updated_at: models.DateTimeField = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["username"]
        verbose_name = "Dressifye kullanıcısı"
        verbose_name_plural = "Dressifye kullanıcıları"

    def __str__(self) -> str:
        return f"{self.username} ({self.external_id})"


class DressifyeGarment(models.Model):
    """Dressifye gardırop öğesinin MEHLR tarafındaki gölge kaydı."""

    external_id: str = models.CharField(max_length=255, unique=True, db_index=True)
    user: models.ForeignKey[DressifyeUser] = models.ForeignKey(
        DressifyeUser,
        on_delete=models.CASCADE,
        related_name="garments",
    )
    name: str = models.CharField(max_length=255)
    category: str = models.CharField(max_length=100, blank=True)
    color: str = models.CharField(max_length=64, blank=True)
    size: str = models.CharField(max_length=32, blank=True)
    image_url: str = models.URLField(max_length=2048, blank=True)
    metadata: dict[str, Any] = models.JSONField(default=dict, blank=True)
    created_at: models.DateTimeField = models.DateTimeField(auto_now_add=True)
    updated_at: models.DateTimeField = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        verbose_name = "Dressifye kıyafet"
        verbose_name_plural = "Dressifye kıyafetleri"

    def __str__(self) -> str:
        return f"{self.name} ({self.external_id})"


class OutfitRecommendation(models.Model):
    """MEHLR tarafından üretilen kombin önerisi; Dressifye ile senkron edilebilir."""

    user: models.ForeignKey[DressifyeUser] = models.ForeignKey(
        DressifyeUser,
        on_delete=models.CASCADE,
        related_name="outfit_recommendations",
    )
    conversation: models.ForeignKey[Conversation] = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="outfit_recommendations",
    )
    garments: models.ManyToManyField[DressifyeGarment] = models.ManyToManyField(
        DressifyeGarment,
        related_name="outfit_recommendations",
        blank=True,
    )
    occasion: str = models.CharField(max_length=100, blank=True)
    style_notes: str = models.TextField(blank=True)
    color_palette: list[Any] | dict[str, Any] = models.JSONField(default=list, blank=True)
    synced_to_dressifye: bool = models.BooleanField(default=False)
    created_at: models.DateTimeField = models.DateTimeField(auto_now_add=True)
    updated_at: models.DateTimeField = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Kombin önerisi"
        verbose_name_plural = "Kombin önerileri"

    def __str__(self) -> str:
        return f"Öneri #{self.pk} — {self.user.username} ({self.occasion or 'genel'})"


class OutfitRecommendationFeedback(models.Model):
    """Dressifye / kullanıcı geri bildirimi (A-B test, kalite)."""

    class FeedbackChoices(models.TextChoices):
        LIKED = "liked", "Beğenildi"
        DISLIKED = "disliked", "Beğenilmedi"

    recommendation: models.ForeignKey[OutfitRecommendation] = models.ForeignKey(
        OutfitRecommendation,
        on_delete=models.CASCADE,
        related_name="feedbacks",
    )
    feedback: str = models.CharField(max_length=32, choices=FeedbackChoices.choices)
    reason: str = models.TextField(blank=True)
    created_at: models.DateTimeField = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Kombin geri bildirimi"
        verbose_name_plural = "Kombin geri bildirimleri"

    def __str__(self) -> str:
        return f"Feedback #{self.pk} — {self.feedback}"
