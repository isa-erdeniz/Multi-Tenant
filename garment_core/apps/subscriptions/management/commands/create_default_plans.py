from decimal import Decimal

from django.core.management.base import BaseCommand

from apps.subscriptions.models import Plan

# USD fiyatlar; mevcut slug ile kayıt varsa get_or_create güncellemez (yalnızca yeni slug oluşturur).
PLANS = [
    {
        "name": "Ücretsiz Deneme",
        "slug": "ucretsiz",
        "price_monthly": Decimal("0"),
        "price_yearly": Decimal("0"),
        "order": 0,
        "tryon_limit": 0,
        "wardrobe_limit": 10,
        "look_limit": 0,
        "editor_limit": 0,
        "style_session_limit": 3,
        # Kota ile sınırlı AI stilist; False yapılırsa styling_new_view tamamen kapanır
        "has_ai_stylist": True,
        "has_advanced_editor": False,
        "has_social_sharing": False,
        "has_priority_support": False,
        "has_hq_export": False,
        "is_popular": False,
        "trial_days": 7,
        "features": [
            "7 gün ücretsiz deneme",
            "Günde 3 stil önerisi",
            "10 kıyafete kadar gardırop",
            "Temel AI analizi",
        ],
    },
    {
        "name": "Stil Plus",
        "slug": "stil-plus",
        "price_monthly": Decimal("5"),
        "price_yearly": Decimal("50"),
        "order": 1,
        "tryon_limit": 10,
        "wardrobe_limit": 50,
        "look_limit": 10,
        "editor_limit": 10,
        "style_session_limit": 0,
        "has_ai_stylist": True,
        "has_advanced_editor": False,
        "has_social_sharing": True,
        "has_priority_support": False,
        "has_hq_export": False,
        "is_popular": True,
        "trial_days": 7,
        "features": [
            "Sınırsız stil önerisi",
            "50 kıyafete kadar gardırop",
            "Sanal deneme — 10/ay",
            "Gelişmiş AI analizi",
            "Sosyal paylaşım",
        ],
    },
    {
        "name": "Stil Pro",
        "slug": "stil-pro",
        "price_monthly": Decimal("10"),
        "price_yearly": Decimal("100"),
        "order": 2,
        "tryon_limit": 0,
        "wardrobe_limit": 0,
        "look_limit": 0,
        "editor_limit": 0,
        "style_session_limit": 0,
        "has_ai_stylist": True,
        "has_advanced_editor": True,
        "has_social_sharing": True,
        "has_priority_support": True,
        "has_hq_export": True,
        "is_popular": False,
        "trial_days": 7,
        "features": [
            "Tüm Stil Plus özellikleri",
            "Sınırsız sanal deneme",
            "Sınırsız gardırop",
            "Gelişmiş editör",
            "Yüksek kalite dışa aktarım",
            "Öncelikli destek — 24 saat",
        ],
    },
]


class Command(BaseCommand):
    help = "Varsayılan planları oluşturur (slug yoksa ekler; varsa dokunmaz)"

    def handle(self, *args, **options):
        created = 0
        for entry in PLANS:
            data = entry.copy()
            features = data.pop("features")
            slug = data.pop("slug")
            defaults = {**data, "features": features, "is_active": True}
            plan, is_new = Plan.objects.get_or_create(
                slug=slug,
                defaults=defaults,
            )
            if is_new:
                created += 1
                self.stdout.write(f"  ✓ {plan.name} ({slug}) oluşturuldu")
            else:
                self.stdout.write(f"  — {slug} zaten mevcut, atlandı")

        self.stdout.write(
            self.style.SUCCESS(f"\n{created} yeni plan oluşturuldu.")
        )
