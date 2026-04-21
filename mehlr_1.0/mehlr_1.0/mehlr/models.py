"""
mehlr_1.0 — Veritabanı modelleri.
ErdenizTech AI Engine için Project, Conversation, Message, AnalysisReport, ModuleRegistry.
"""
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
