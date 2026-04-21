from django.db import models
from django.contrib.auth import get_user_model

from apps.core.models import TenantModel, TimeStampedModel

User = get_user_model()


class GarmentCategory(TimeStampedModel):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    icon = models.CharField(max_length=50, blank=True, help_text="Emoji veya Lucide icon adı")
    color = models.CharField(max_length=7, default="#C9A84C")
    order = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Kategori"
        verbose_name_plural = "Kategoriler"
        ordering = ["order", "name"]

    def __str__(self):
        return self.name


class Garment(TenantModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="garments")
    category = models.ForeignKey(
        GarmentCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="garments",
    )

    name = models.CharField(max_length=200)
    color = models.CharField(max_length=50, blank=True)
    color_hex = models.CharField(max_length=7, blank=True, help_text="#RRGGBB")
    brand = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)

    SUBCATEGORY_CHOICES = [
        ("ust", "Üst Giyim"),
        ("alt", "Alt Giyim"),
        ("dis", "Dış Giyim"),
        ("ayakkabi", "Ayakkabı"),
        ("aksesuar", "Aksesuar"),
    ]
    subcategory = models.CharField(max_length=50, choices=SUBCATEGORY_CHOICES, blank=True)

    PATTERN_CHOICES = [
        ("duz", "Düz"),
        ("cizgili", "Çizgili"),
        ("puanli", "Puanlı"),
        ("cicekli", "Çiçekli"),
        ("ekose", "Ekose"),
    ]
    pattern = models.CharField(max_length=20, choices=PATTERN_CHOICES, blank=True)

    size = models.CharField(max_length=20, blank=True)
    material = models.CharField(max_length=100, blank=True)

    SEASON_CHOICES = [
        ("4mevsim", "4 Mevsim"),
        ("yaz", "Yaz"),
        ("kis", "Kış"),
        ("bahar", "Bahar"),
        ("sonbahar", "Sonbahar"),
        ("all", "Her Mevsim"),
        ("spring", "İlkbahar/Yaz"),
        ("fall", "Sonbahar/Kış"),
    ]
    season = models.CharField(max_length=20, choices=SEASON_CHOICES, default="4mevsim")

    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    purchase_date = models.DateField(null=True, blank=True)
    store_name = models.CharField(max_length=100, blank=True)
    purchase_url = models.URLField(blank=True)

    times_worn = models.PositiveIntegerField(default=0)
    last_worn = models.DateField(null=True, blank=True)
    is_favorite = models.BooleanField(default=False)

    image = models.ImageField(upload_to="garments/%Y/%m/")
    thumbnail = models.ImageField(upload_to="garments/thumbs/%Y/%m/", blank=True)
    is_ai_processed = models.BooleanField(default=False, help_text="Arka plan temizlendi mi?")

    tags = models.JSONField(default=list, blank=True)
    ai_analysis = models.JSONField(null=True, blank=True)
    ai_analyzed_at = models.DateTimeField(null=True, blank=True)

    is_active = models.BooleanField(default=True)
    slug = models.SlugField(max_length=120, blank=True, null=True)

    class Meta:
        verbose_name = "Kıyafet"
        verbose_name_plural = "Kıyafetler"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.email} — {self.name}"

    def get_tags_display(self):
        return ", ".join(self.tags) if self.tags else ""

    def save(self, *args, **kwargs):
        from django.utils.text import slugify
        import uuid

        if not self.slug and (self.name or self.pk):
            self.slug = slugify(self.name or "item")[:50] + "-" + str(uuid.uuid4())[:6]
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse("wardrobe:detail", kwargs={"pk": self.pk})

    @property
    def image_url(self):
        """Görsel URL'ini güvenli döndürür; hata veya yoksa placeholder."""
        try:
            if self.image and hasattr(self.image, "url"):
                return self.image.url
        except (ValueError, OSError):
            pass
        return "/static/images/placeholder-garment.svg"


class WardrobeTag(TenantModel):
    """AI veya manuel etiket."""
    garment = models.ForeignKey(
        Garment, on_delete=models.CASCADE, related_name="wardrobe_tags"
    )
    tag_name = models.CharField(max_length=50)
    tag_value = models.CharField(max_length=100, blank=True)
    ai_generated = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Gardırop Etiketi"
        verbose_name_plural = "Gardırop Etiketleri"


class Outfit(TenantModel):
    """Kombin (sürükle-bırak ile oluşturulan)."""
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="outfits"
    )
    name = models.CharField(max_length=200)
    garments = models.ManyToManyField(
        Garment, blank=True, related_name="outfits"
    )
    occasion = models.CharField(max_length=100, blank=True)
    season = models.CharField(max_length=20, blank=True)
    rating = models.PositiveSmallIntegerField(null=True, blank=True)

    class Meta:
        verbose_name = "Kombin"
        verbose_name_plural = "Kombinler"
        ordering = ["-created_at"]


class WearLog(TenantModel):
    """Giyim kaydı (bugün ne giydim)."""
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="wear_logs"
    )
    outfit = models.ForeignKey(
        Outfit, on_delete=models.SET_NULL, null=True, blank=True, related_name="wear_logs"
    )
    garment = models.ForeignKey(
        Garment, on_delete=models.SET_NULL, null=True, blank=True, related_name="wear_logs"
    )
    date = models.DateField()
    weather = models.CharField(max_length=50, blank=True)
    occasion = models.CharField(max_length=100, blank=True)
    photo = models.ImageField(upload_to="wearlog/%Y/%m/", null=True, blank=True)

    class Meta:
        verbose_name = "Giyim Kaydı"
        verbose_name_plural = "Giyim Kayıtları"
        ordering = ["-date"]
