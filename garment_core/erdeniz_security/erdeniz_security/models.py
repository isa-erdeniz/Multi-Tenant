"""SecurityAuditLog ve ErdenizAPIKey modelleri."""
import uuid
from django.db import models
from django.conf import settings

EVENT_TYPES = [
    ("ENCRYPT", "Veri Şifrelendi"),
    ("DECRYPT", "Veri Çözüldü"),
    ("AUTH_SUCCESS", "Başarılı Giriş"),
    ("AUTH_FAIL", "Başarısız Giriş"),
    ("KEY_ROTATE", "Anahtar Rotasyonu"),
    ("ENV_ENCRYPT", ".env Şifrelendi"),
    ("ENV_DECRYPT", ".env Çözüldü"),
    ("FILE_ENCRYPT", "Dosya Şifrelendi"),
    ("FILE_DECRYPT", "Dosya Çözüldü"),
    ("SECURITY_ALERT", "Güvenlik Uyarısı"),
    ("CONFIG_CHANGE", "Ayar Değişikliği"),
    ("API_KEY_CREATE", "API Key Üretildi"),
    ("API_KEY_REVOKE", "API Key İptal Edildi"),
    ("API_KEY_ROTATE", "API Key Döndürüldü"),
    ("API_AUTH_SUCCESS", "API Doğrulama Başarılı"),
    ("API_AUTH_FAIL", "API Doğrulama Başarısız"),
    ("RATE_LIMIT_HIT", "Rate Limit Aşıldı"),
    ("WEBHOOK_VERIFIED", "Webhook Doğrulandı"),
    ("WEBHOOK_REJECTED", "Webhook Reddedildi"),
    ("SUSPICIOUS_IP", "Şüpheli IP Erişimi"),
    ("CORS_VIOLATION", "CORS İhlali"),
]


class SecurityAuditLog(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    event_type = models.CharField(max_length=50, choices=EVENT_TYPES)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    resource = models.CharField(max_length=255)
    project = models.CharField(max_length=50)
    success = models.BooleanField(default=True)
    details = models.JSONField(default=dict, blank=True)
    duration_ms = models.IntegerField(null=True, blank=True)

    class Meta:
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["event_type", "timestamp"]),
            models.Index(fields=["project", "timestamp"]),
            models.Index(fields=["user_id", "timestamp"]),
        ]
        verbose_name = "Güvenlik Denetim Kaydı"
        verbose_name_plural = "Güvenlik Denetim Kayıtları"


class ErdenizAPIKey(models.Model):
    """API key; tam değer asla saklanmaz, sadece Argon2 hash."""
    key_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    prefix = models.CharField(max_length=8, unique=True, db_index=True)
    hashed_key = models.CharField(max_length=255)
    project = models.CharField(max_length=50)
    permissions = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    last_used_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    usage_count = models.IntegerField(default=0)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["project", "is_active"]),
            models.Index(fields=["prefix"]),
        ]
        verbose_name = "API Key"
        verbose_name_plural = "API Keys"
