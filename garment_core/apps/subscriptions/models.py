from decimal import Decimal

from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.core.models import TimeStampedModel

User = get_user_model()


class Plan(TimeStampedModel):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    price_monthly = models.DecimalField(
        max_digits=8, decimal_places=2, default=0
    )
    price_yearly = models.DecimalField(
        max_digits=8, decimal_places=2, default=0
    )
    features = models.JSONField(default=list)
    is_active = models.BooleanField(default=True)
    order = models.PositiveSmallIntegerField(default=0)

    tryon_limit = models.PositiveIntegerField(
        "Aylık sanal deneme limiti",
        default=3,
        help_text="0 = sınırsız",
    )
    wardrobe_limit = models.PositiveIntegerField(
        "Maksimum gardırop öğesi",
        default=10,
        help_text="0 = sınırsız",
    )
    look_limit = models.PositiveIntegerField(
        "Maksimum görünüm (look)",
        default=5,
        help_text="0 = sınırsız",
    )
    editor_limit = models.PositiveIntegerField(
        "Aylık editör kullanımı",
        default=5,
        help_text="0 = sınırsız",
    )
    style_session_limit = models.PositiveIntegerField(
        "Aylık stil danışmanlığı",
        default=5,
        help_text="0 = sınırsız",
    )

    has_ai_stylist = models.BooleanField("AI stilist", default=False)
    has_advanced_editor = models.BooleanField("Gelişmiş editör", default=False)
    has_social_sharing = models.BooleanField("Sosyal paylaşım", default=False)
    has_priority_support = models.BooleanField("Öncelikli destek", default=False)
    has_hq_export = models.BooleanField("Yüksek kalite dışa aktarım", default=False)

    is_popular = models.BooleanField("Popüler plan", default=False)
    trial_days = models.PositiveSmallIntegerField(
        "Deneme süresi (gün)",
        default=7,
    )

    ai_credits_monthly = models.PositiveIntegerField(
        "Aylık harici AI kredisi",
        default=0,
        help_text="0 = bu planda harici AI kotası yok.",
    )
    external_ai_enabled = models.BooleanField(
        "Harici AI (WearView / Zmo / Style3D)",
        default=False,
    )

    class Meta:
        ordering = ["order"]
        verbose_name = "Plan"
        verbose_name_plural = "Planlar"

    def __str__(self):
        return self.name

    @property
    def is_free(self):
        return self.price_monthly == 0

    @property
    def yearly_savings(self) -> Decimal:
        """Aylık x12 ile yıllık fiyat arasındaki fark (yıllık seçimde tasarruf)."""
        if self.is_free:
            return Decimal("0")
        return (self.price_monthly * Decimal("12")) - self.price_yearly

    def has_feature(self, feature_name: str) -> bool:
        """feature_name: ai_stylist, advanced_editor, social_sharing, priority_support, hq_export"""
        mapping = {
            "ai_stylist": self.has_ai_stylist,
            "advanced_editor": self.has_advanced_editor,
            "social_sharing": self.has_social_sharing,
            "priority_support": self.has_priority_support,
            "hq_export": self.has_hq_export,
        }
        if feature_name not in mapping:
            return False
        return bool(mapping[feature_name])


class UserSubscription(TimeStampedModel):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="subscription"
    )
    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.CASCADE,
        related_name="subscriptions",
        help_text="Ödeme ve kota bağlamı; kullanıcının tenant'ı ile eşleşmeli.",
    )
    plan = models.ForeignKey(
        Plan, on_delete=models.SET_NULL, null=True, related_name="subscriptions"
    )

    STATUS_CHOICES = [
        ("trial", "Deneme"),
        ("active", "Aktif"),
        ("cancelled", "İptal Edildi"),
        ("expired", "Süresi Doldu"),
        ("past_due", "Ödeme Gecikti"),
    ]
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="trial"
    )
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField(null=True, blank=True)

    iyzico_subscription_ref = models.CharField(max_length=200, blank=True)
    iyzico_customer_ref = models.CharField(max_length=200, blank=True)

    ai_credits_used = models.PositiveIntegerField(
        "Kullanılan harici AI kredisi (dönem)",
        default=0,
    )
    ai_credits_reset_date = models.DateTimeField(
        "Harici AI kredi sıfırlama zamanı",
        null=True,
        blank=True,
        help_text="Boşsa ilk kullanımda ay başına göre atanır.",
    )

    class Meta:
        verbose_name = "Abonelik"
        verbose_name_plural = "Abonelikler"

    def __str__(self):
        plan_name = self.plan.name if self.plan else "—"
        return f"{self.user.email} — {plan_name} ({self.status})"

    def is_active(self):
        if self.status == "trial":
            return self.end_date is None or self.end_date > timezone.now()
        return self.status == "active"

    def trial_days_left(self):
        if self.status != "trial" or self.end_date is None:
            return 0
        delta = self.end_date - timezone.now()
        return max(0, delta.days)

    def is_trial_expired(self):
        if self.status != "trial":
            return False
        if self.end_date is None:
            return False
        return timezone.now() > self.end_date


class UsageQuota(TimeStampedModel):
    """FAZ 16: Plan bazlı kullanım kotası (eski; FeatureUsage ile birlikte kullanılabilir)."""
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="usage_quota"
    )
    tryon_count = models.PositiveIntegerField(default=0)
    editor_count = models.PositiveIntegerField(default=0)
    wardrobe_count = models.PositiveIntegerField(default=0)
    reset_date = models.DateField(null=True, blank=True)

    class Meta:
        verbose_name = "Kullanım Kotası"
        verbose_name_plural = "Kullanım Kotaları"


class FeatureUsage(TimeStampedModel):
    """Tenant bazlı aylık özellik kullanımı (paylaşımlı kota)."""

    FEATURE_TRYON = "tryon"
    FEATURE_EDITOR = "editor"
    FEATURE_STYLE_SESSION = "style_session"
    FEATURE_LOOK_CREATE = "look_create"

    FEATURE_CHOICES = [
        (FEATURE_TRYON, "Sanal Deneme"),
        (FEATURE_EDITOR, "Görsel Editör"),
        (FEATURE_STYLE_SESSION, "Stil Danışmanlığı"),
        (FEATURE_LOOK_CREATE, "Görünüm Oluşturma"),
    ]

    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.CASCADE,
        related_name="feature_usages",
    )
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="feature_usages",
        help_text="İsteğe bağlı: son işlemi yapan kullanıcı (denetim).",
    )
    feature_type = models.CharField(max_length=50, choices=FEATURE_CHOICES)
    month = models.DateField(
        help_text="Ayın ilk günü (örn. 2024-01-01)",
    )
    count = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Özellik Kullanımı"
        verbose_name_plural = "Özellik Kullanımları"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "feature_type", "month"],
                name="subscriptions_featureusage_tenant_feature_month_uniq",
            ),
        ]
        indexes = [
            models.Index(fields=["tenant", "month"]),
            models.Index(fields=["user", "month"]),
        ]

    def __str__(self):
        return f"tenant={self.tenant_id} {self.feature_type} {self.month} = {self.count}"
