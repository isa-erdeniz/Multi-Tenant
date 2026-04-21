"""python manage.py rotate_field_key"""
from django.core.management.base import BaseCommand
from erdeniz_security.encryption import generate_field_encryption_key
from erdeniz_security.audit import log_event


class Command(BaseCommand):
    help = "Yeni FIELD_ENCRYPTION_KEY üretir (rotasyon)"

    def handle(self, *args, **options):
        key = generate_field_encryption_key()
        log_event("KEY_ROTATE", "FIELD_ENCRYPTION_KEY", "erdeniz_security", success=True)
        self.stdout.write("Yeni FIELD_ENCRYPTION_KEY (.env güncelle, sonra encrypt_existing çalıştır):")
        self.stdout.write(self.style.SUCCESS(key))
