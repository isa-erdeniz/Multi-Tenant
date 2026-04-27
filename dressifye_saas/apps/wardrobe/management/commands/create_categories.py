from django.core.management.base import BaseCommand

from apps.wardrobe.models import GarmentCategory


class Command(BaseCommand):
    help = "Varsayılan kıyafet kategorilerini oluşturur"

    def handle(self, *args, **options):
        categories = [
            ("Üst Giyim", "ust-giyim", "👕", "#3B82F6", 1),
            ("Alt Giyim", "alt-giyim", "👖", "#10B981", 2),
            ("Elbise", "elbise", "👗", "#EC4899", 3),
            ("Dış Giyim", "dis-giyim", "🧥", "#F59E0B", 4),
            ("Ayakkabı", "ayakkabi", "👟", "#8B5CF6", 5),
            ("Aksesuar", "aksesuar", "👜", "#EC4899", 6),
            ("Spor", "spor", "🏃", "#14B8A6", 7),
            ("İç Giyim", "ic-giyim", "🩲", "#94A3B8", 8),
        ]
        created = 0
        for name, slug, icon, color, order in categories:
            _, is_new = GarmentCategory.objects.get_or_create(
                slug=slug,
                defaults={"name": name, "icon": icon, "color": color, "order": order},
            )
            if is_new:
                created += 1

        self.stdout.write(self.style.SUCCESS(f"{created} kategori oluşturuldu."))
