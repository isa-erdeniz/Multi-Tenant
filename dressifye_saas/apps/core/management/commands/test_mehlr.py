import json

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.core.clients.mehlr_client import MEHLRClient


class Command(BaseCommand):
    help = "MEHLR bağlantısını test eder"

    def handle(self, *args, **options):
        client = MEHLRClient()

        self.stdout.write("MEHLR health check...")
        if client.health_check():
            self.stdout.write(self.style.SUCCESS("✓ MEHLR ayakta"))
        else:
            self.stdout.write(self.style.ERROR("✗ MEHLR yanıt vermiyor"))
            return

        self.stdout.write("\nTest analizi gönderiliyor...")
        result = client.analyze(
            project=settings.MEHLR_PROJECT,
            prompt="Mavi kot pantolon ile beyaz gömlek kombini öner",
            context={
                "task": "test",
                "wardrobe": [
                    {
                        "id": 1,
                        "name": "Beyaz gömlek",
                        "category": "Üst Giyim",
                        "color": "Beyaz",
                    },
                    {
                        "id": 2,
                        "name": "Mavi kot",
                        "category": "Alt Giyim",
                        "color": "Mavi",
                    },
                    {
                        "id": 3,
                        "name": "Beyaz spor ayakkabı",
                        "category": "Ayakkabı",
                        "color": "Beyaz",
                    },
                ],
            },
        )

        if result.get("success"):
            self.stdout.write(self.style.SUCCESS("✓ MEHLR yanıt verdi"))
            self.stdout.write(
                json.dumps(result["data"], indent=2, ensure_ascii=False)
            )
        else:
            self.stdout.write(
                self.style.ERROR(f"✗ MEHLR hata: {result.get('error')}")
            )
