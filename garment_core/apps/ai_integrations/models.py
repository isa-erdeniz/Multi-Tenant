"""
Harici AI sağlayıcı yapılandırması, iş kuyruğu kayıtları ve kota denetim günlüğü.
"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from typing import Any

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from django_cryptography.fields import encrypt

from apps.core.models import TenantModel


class AIProvider(models.Model):
    """Harici AI servis uç noktası ve anahtar (DB'de şifreli)."""

    NAME_WEARVIEW = "wearview"
    NAME_ZMO = "zmo"
    NAME_STYLE3D = "style3d"

    NAME_CHOICES = [
        (NAME_WEARVIEW, "WearView"),
        (NAME_ZMO, "Zmo.ai"),
        (NAME_STYLE3D, "Style3D"),
    ]

    name = models.CharField(
        max_length=32,
        choices=NAME_CHOICES,
        unique=True,
        db_index=True,
    )
    display_name = models.CharField(
        _("Görünen ad"),
        max_length=120,
        blank=True,
        help_text=_("Admin listelerinde gösterilir; boşsa name kullanılır."),
    )
    api_key_encrypted = encrypt(models.TextField(blank=True))
    webhook_secret_encrypted = encrypt(
        models.TextField(
            blank=True,
            help_text=_("Webhook HMAC doğrulaması (boşsa ortam değişkeni kullanılır)."),
        )
    )
    base_url = models.URLField(max_length=500)
    is_active = models.BooleanField(default=True)
    rate_limit_per_minute = models.PositiveIntegerField(
        default=60,
        help_text=_("Dakika başına en fazla istek (önbellek penceresi)."),
    )
    cost_per_request = models.DecimalField(
        _("Birim maliyet (bilgi)"),
        max_digits=10,
        decimal_places=4,
        default=Decimal("0"),
        help_text=_("Fiyatlandırma / raporlama için; kota hâlâ plandan."),
    )
    supports_sync = models.BooleanField(_("Senkron yanıt destekler"), default=True)
    supports_async = models.BooleanField(_("Asenkron iş destekler"), default=True)
    fallback_provider = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="primary_for",
        help_text=_("Birincil sağlayıcı kullanılamazsa denenecek yedek."),
    )
    config = models.JSONField(
        default=dict,
        blank=True,
        help_text=_("Sağlayıcıya özel uç yolları ve ek parametreler."),
    )

    class Meta:
        verbose_name = _("AI sağlayıcı")
        verbose_name_plural = _("AI sağlayıcılar")

    def __str__(self) -> str:
        return self.display_name.strip() or self.get_name_display()

    def get_webhook_secret(self) -> str:
        """
        Webhook HMAC için gizli anahtar (şifreli alan çözülmüş).

        Returns:
            Boşlukları kırpılmış gizli dize; yoksa boş string.
        """
        return (self.webhook_secret_encrypted or "").strip()


class AIProcessingTask(TenantModel):
    """Harici AI işlemi için tek bir istek kaydı."""

    TASK_TRYON = "tryon"
    TASK_MODEL_GENERATION = "model_generation"
    TASK_TEXTURE = "texture_creation"
    TASK_BACKGROUND_REMOVAL = "background_removal"
    TASK_POSE_TRANSFER = "pose_transfer"
    TASK_GARMENT_3D = "garment_3d"
    TASK_PATTERN_GENERATION = "pattern_generation"
    TASK_FABRIC_SIMULATION = "fabric_simulation"

    TASK_TYPE_CHOICES = [
        (TASK_TRYON, _("Sanal deneme")),
        (TASK_MODEL_GENERATION, _("Model üretimi")),
        (TASK_TEXTURE, _("Doku / kumaş üretimi")),
        (TASK_BACKGROUND_REMOVAL, _("Arka plan kaldırma")),
        (TASK_POSE_TRANSFER, _("Poz aktarımı")),
        (TASK_GARMENT_3D, _("3D kıyafet")),
        (TASK_PATTERN_GENERATION, _("Desen üretimi")),
        (TASK_FABRIC_SIMULATION, _("Kumaş simülasyonu")),
    ]

    STATUS_QUEUED = "queued"
    STATUS_PROCESSING = "processing"
    STATUS_COMPLETED = "completed"
    STATUS_FAILED = "failed"
    STATUS_CANCELLED = "cancelled"

    STATUS_CHOICES = [
        (STATUS_QUEUED, _("Kuyrukta")),
        (STATUS_PROCESSING, _("İşleniyor")),
        (STATUS_COMPLETED, _("Tamamlandı")),
        (STATUS_FAILED, _("Başarısız")),
        (STATUS_CANCELLED, _("İptal")),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ai_processing_tasks",
    )
    provider = models.ForeignKey(
        AIProvider,
        on_delete=models.PROTECT,
        related_name="tasks",
    )
    task_type = models.CharField(max_length=64, choices=TASK_TYPE_CHOICES)
    status = models.CharField(
        max_length=32,
        choices=STATUS_CHOICES,
        default=STATUS_QUEUED,
        db_index=True,
    )
    priority = models.PositiveSmallIntegerField(
        _("Öncelik"),
        default=5,
        help_text=_("1 en yüksek (ileride kuyruk sıralaması için)."),
    )
    input_data = models.JSONField(default=dict, blank=True)
    output_data = models.JSONField(
        default=dict,
        blank=True,
        help_text=_(
            "Anahtarlar: submit (API gönderimi), api_trail (failover), "
            "last_failure (hata ayıklama), webhook (geri çağırma yükü)."
        ),
    )
    credits_used = models.PositiveIntegerField(default=0)
    estimated_credits = models.PositiveIntegerField(
        _("Tahmini kredi"),
        default=0,
        help_text=_("İş kuyruğa alınırken hesaplanan değer."),
    )
    error_message = models.TextField(blank=True)
    retry_count = models.PositiveSmallIntegerField(default=0)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    webhook_received_at = models.DateTimeField(
        _("Webhook alındı"),
        null=True,
        blank=True,
    )
    external_task_id = models.CharField(max_length=255, blank=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("AI işlem kaydı")
        verbose_name_plural = _("AI işlem kayıtları")
        indexes = [
            models.Index(fields=["tenant", "status"]),
            models.Index(fields=["tenant", "created_at"]),
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["tenant", "external_task_id"]),
            models.Index(fields=["provider", "external_task_id"]),
        ]

    def __str__(self) -> str:
        return f"task={self.pk} {self.task_type} ({self.status})"

    @property
    def is_terminal_status(self) -> bool:
        """Görev sonlandı mı?"""
        return self.status in {
            self.STATUS_COMPLETED,
            self.STATUS_FAILED,
            self.STATUS_CANCELLED,
        }

    @property
    def processing_duration(self) -> timedelta | None:
        """Başlangıç ile bitiş arası süre (varsa)."""
        if not self.started_at or not self.completed_at:
            return None
        return self.completed_at - self.started_at

    def record_failure(
        self,
        error_type: str,
        message: str,
        context: dict[str, Any] | None = None,
        raw_response: str | None = None,
    ) -> None:
        """
        Hata özetini ``output_data['last_failure']`` altında saklar (DB'ye kaydetmez).

        Args:
            error_type: İstisna veya kısa kod adı.
            message: İnsan okunur mesaj.
            context: Ek yapılandırılmış alanlar (status_code vb.).
            raw_response: Ham HTTP gövdesi (en fazla 1000 karakter saklanır).
        """
        out: dict[str, Any] = dict(self.output_data or {})
        rr = (raw_response or "")[:1000] if raw_response else ""
        out["last_failure"] = {
            "type": error_type,
            "message": (message or "")[:4000],
            "context": dict(context or {}),
            "raw_response": rr,
        }
        self.output_data = out

    def get_result_urls(self) -> list[str]:
        """
        ``output_data`` içinden olası sonuç URL'lerini çıkarır (sıra korunur, tekilleştirilir).

        Returns:
            http(s) ile başlayan URL listesi.
        """
        found: list[str] = []
        seen: set[str] = set()
        od = self.output_data or {}

        def add(u: str) -> None:
            if isinstance(u, str) and u.startswith("http") and u not in seen:
                seen.add(u)
                found.append(u)

        for key in ("result_urls", "output_urls", "image_urls"):
            val = od.get(key)
            if isinstance(val, list):
                for item in val:
                    add(str(item))
        for blob in (od.get("webhook"), od.get("submit")):
            if isinstance(blob, dict):
                for k in ("url", "result_url", "image_url", "output_url", "garment_image"):
                    v = blob.get(k)
                    if isinstance(v, str):
                        add(v)
        return found


class AIQuotaLog(TenantModel):
    """Kredi düşümü / iade denetim günlüğü."""

    TX_USAGE = "usage"
    TX_REFUND = "refund"
    TX_ADJUSTMENT = "adjustment"
    TX_BONUS = "bonus"

    TRANSACTION_CHOICES = [
        (TX_USAGE, _("Kullanım")),
        (TX_REFUND, _("İade")),
        (TX_ADJUSTMENT, _("Düzeltme")),
        (TX_BONUS, _("Bonus")),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ai_quota_logs",
    )
    task = models.ForeignKey(
        AIProcessingTask,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="quota_logs",
    )
    credits_used = models.PositiveIntegerField(
        default=0,
        help_text=_("Eski alan: mutlak miktar (geriye dönük uyumluluk)."),
    )
    note = models.CharField(max_length=255, blank=True)
    transaction_type = models.CharField(
        max_length=32,
        choices=TRANSACTION_CHOICES,
        default=TX_USAGE,
        db_index=True,
    )
    credits_amount = models.IntegerField(
        _("İşaretli miktar"),
        default=0,
        help_text=_("Kullanım için negatif, iade için pozitif."),
    )
    balance_before = models.PositiveIntegerField(
        _("Önceki kullanılan kota"),
        null=True,
        blank=True,
    )
    balance_after = models.PositiveIntegerField(
        _("Sonraki kullanılan kota"),
        null=True,
        blank=True,
    )
    description = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("AI kota günlüğü")
        verbose_name_plural = _("AI kota günlükleri")
        indexes = [
            models.Index(fields=["tenant", "created_at"]),
            models.Index(fields=["tenant", "transaction_type"]),
        ]

    def __str__(self) -> str:
        return f"log={self.pk} task={self.task_id} amt={self.credits_amount}"
