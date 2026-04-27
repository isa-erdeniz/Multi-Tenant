from django.db import models
from django.contrib.auth import get_user_model

from apps.core.models import TimeStampedModel

User = get_user_model()


class BodyMeasurement(TimeStampedModel):
    """Detaylı vücut ölçümleri (göğüs, bel, kalça, omuz, kol, bacak)."""
    profile = models.OneToOneField(
        "UserProfile",
        on_delete=models.CASCADE,
        related_name="body_measurement",
        null=True,
        blank=True,
    )
    shoulder_width = models.PositiveSmallIntegerField(null=True, blank=True, help_text="Omuz genişliği (cm)")
    arm_length = models.PositiveSmallIntegerField(null=True, blank=True, help_text="Kol uzunluğu (cm)")
    leg_length = models.PositiveSmallIntegerField(null=True, blank=True, help_text="İç bacak uzunluğu (cm)")
    neck = models.PositiveSmallIntegerField(null=True, blank=True, help_text="Boyun çevresi (cm)")

    class Meta:
        verbose_name = "Vücut Ölçümü"
        verbose_name_plural = "Vücut Ölçümleri"


class SizePreference(TimeStampedModel):
    """Beden sistemi ve tercihleri (TR/EU/US/UK)."""
    profile = models.OneToOneField(
        "UserProfile",
        on_delete=models.CASCADE,
        related_name="size_preference",
        null=True,
        blank=True,
    )
    SIZE_SYSTEM_CHOICES = [
        ("tr", "Türkiye"),
        ("eu", "Avrupa (EU)"),
        ("us", "ABD (US)"),
        ("uk", "İngiltere (UK)"),
    ]
    size_system = models.CharField(max_length=5, choices=SIZE_SYSTEM_CHOICES, default="tr")
    top_size = models.CharField(max_length=20, blank=True)  # üst beden
    bottom_size = models.CharField(max_length=20, blank=True)  # alt beden
    shoe_size = models.CharField(max_length=10, blank=True)

    class Meta:
        verbose_name = "Beden Tercihi"
        verbose_name_plural = "Beden Tercihleri"


class UserAvatar(TimeStampedModel):
    """Kullanıcı fotoğrafından oluşturulan avatar."""
    profile = models.OneToOneField(
        "UserProfile",
        on_delete=models.CASCADE,
        related_name="user_avatar",
        null=True,
        blank=True,
    )
    avatar_image = models.ImageField(upload_to="avatars/generated/%Y/%m/", null=True, blank=True)
    body_type = models.CharField(max_length=30, blank=True)
    skin_tone = models.CharField(max_length=20, blank=True)

    class Meta:
        verbose_name = "Kullanıcı Avatarı"
        verbose_name_plural = "Kullanıcı Avatarları"


class UserProfile(TimeStampedModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")

    # Temel bilgiler
    first_name = models.CharField(max_length=100, blank=True)
    avatar = models.ImageField(upload_to="avatars/%Y/%m/", null=True, blank=True)
    city = models.CharField(max_length=100, blank=True, help_text="Hava durumu için şehir (örn: İstanbul, İzmir)")

    # Vücut ölçüleri (cm / kg)
    height = models.PositiveSmallIntegerField(null=True, blank=True, help_text="cm")
    weight = models.PositiveSmallIntegerField(null=True, blank=True, help_text="kg")
    bust = models.PositiveSmallIntegerField(null=True, blank=True, help_text="cm")
    waist = models.PositiveSmallIntegerField(null=True, blank=True, help_text="cm")
    hips = models.PositiveSmallIntegerField(null=True, blank=True, help_text="cm")

    BODY_SHAPE_CHOICES = [
        ("hourglass", "Kum Saati"),
        ("pear", "Armut"),
        ("apple", "Elma"),
        ("rectangle", "Dikdörtgen"),
        ("inverted_triangle", "Ters Üçgen"),
    ]
    body_shape = models.CharField(max_length=30, choices=BODY_SHAPE_CHOICES, blank=True)

    # Stil tercihleri — çoklu seçim, JSON olarak saklanır
    preferred_styles = models.JSONField(default=list, blank=True)

    # Renk tercihleri
    SKIN_TONE_CHOICES = [
        ("light", "Açık"),
        ("medium", "Orta"),
        ("olive", "Zeytinyağı"),
        ("dark", "Koyu"),
        ("deep", "Derin"),
    ]
    skin_tone = models.CharField(max_length=20, choices=SKIN_TONE_CHOICES, blank=True)

    # Onboarding tamamlandı mı?
    onboarding_completed = models.BooleanField(default=False)
    onboarding_step = models.PositiveSmallIntegerField(default=1)

    # Gizlilik ayarları: hangi veriler paylaşılabilir
    PRIVACY_CHOICES = [
        ("private", "Gizli"),
        ("anon", "Anonim"),
        ("public", "Herkese açık"),
    ]
    measurement_privacy = models.CharField(
        max_length=10, choices=PRIVACY_CHOICES, default="private"
    )
    profile_privacy = models.CharField(
        max_length=10, choices=PRIVACY_CHOICES, default="private"
    )

    # Dressifye vitrin aboneliği (dressifye_saas API + iyzico Subscription)
    DRESSIFYE_TIER_CHOICES = [
        ("", "—"),
        ("starter", "Starter"),
        ("elite", "Elite"),
        ("platinum", "Platinum"),
        ("diamond", "Diamond"),
    ]
    dressifye_marketing_tier = models.CharField(
        max_length=20,
        choices=DRESSIFYE_TIER_CHOICES,
        blank=True,
        default="",
    )
    dressifye_display_title = models.CharField(
        max_length=120,
        blank=True,
        default="",
        help_text="Örn. Princess Duygu — vitrin / rapor başlığı",
    )
    feature_voice_ai = models.BooleanField(
        "Sesli AI asistan",
        default=False,
    )
    feature_white_label_reports = models.BooleanField(
        "White-label raporlar",
        default=False,
    )

    def __str__(self):
        return f"{self.user.email} profili"

    def get_display_name(self):
        return self.first_name or self.user.email.split("@")[0]
