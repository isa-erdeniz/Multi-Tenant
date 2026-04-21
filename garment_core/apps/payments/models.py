import hashlib

from django.db import models
from django.contrib.auth import get_user_model

from apps.core.models import TimeStampedModel

User = get_user_model()


class WebhookEvent(TimeStampedModel):
    """
    iyzico webhook idempotency: aynı iyziReferenceCode (veya gövde özeti) tekrar
    işlenmez; çift abonelik uzatma / ödeme güncellemesi önlenir.
    """

    reference_code = models.CharField(
        max_length=128,
        unique=True,
        db_index=True,
        help_text="iyziReferenceCode veya içerik özeti",
    )
    event_type = models.CharField(max_length=120, blank=True)

    class Meta:
        verbose_name = "Webhook olayı"
        verbose_name_plural = "Webhook olayları"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.event_type or '?'} — {self.reference_code[:16]}…"


def webhook_idempotency_key(payload: dict, raw_body: bytes) -> str:
    """Benzersiz anahtar: önce iyziReferenceCode, yoksa SHA-256(gövde + event tipi)."""
    ref = payload.get("iyziReferenceCode")
    if ref:
        return str(ref)[:128]
    et = (
        str(payload.get("iyziEventType") or payload.get("eventType") or "")
    ).encode()
    digest = hashlib.sha256(raw_body + et).hexdigest()
    return f"body:{digest}"


class Payment(TimeStampedModel):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="payments"
    )
    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.CASCADE,
        related_name="payments",
        help_text="Ödeme anındaki tenant; callback'te kullanıcı ile doğrulanır.",
    )
    plan = models.ForeignKey(
        "subscriptions.Plan", on_delete=models.SET_NULL, null=True
    )

    iyzico_token = models.CharField(max_length=200, blank=True)
    iyzico_payment_id = models.CharField(max_length=200, blank=True)
    iyzico_conversation_id = models.CharField(max_length=200, blank=True)

    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default="TRY")

    PERIOD_CHOICES = [
        ("monthly", "Aylık"),
        ("yearly", "Yıllık"),
    ]
    period = models.CharField(
        max_length=10, choices=PERIOD_CHOICES, default="monthly"
    )

    STATUS_CHOICES = [
        ("pending", "Bekliyor"),
        ("success", "Başarılı"),
        ("failed", "Başarısız"),
        ("refunded", "İade Edildi"),
    ]
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="pending"
    )
    failure_reason = models.TextField(blank=True)

    PAYMENT_KIND_CHOICES = [
        ("checkout", "Tek seferlik CheckoutForm"),
        ("subscription_checkout", "Abonelik CheckoutForm"),
    ]
    payment_kind = models.CharField(
        max_length=40,
        choices=PAYMENT_KIND_CHOICES,
        default="checkout",
    )
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = "Ödeme"
        verbose_name_plural = "Ödemeler"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.email} — ₺{self.amount} ({self.status})"
