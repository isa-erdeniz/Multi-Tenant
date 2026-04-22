"""Fernet veya field encryption anahtarı üretir. Kurulum script'i için."""
from django.core.management.base import BaseCommand
from erdeniz_security.encryption import generate_key, generate_field_encryption_key


class Command(BaseCommand):
    help = "ERDENIZ_ENCRYPTION_KEY veya FIELD_ENCRYPTION_KEY üretir"

    def add_arguments(self, parser):
        parser.add_argument("--type", choices=["fernet", "field"], default="fernet")

    def handle(self, *args, **options):
        if options["type"] == "field":
            self.stdout.write(generate_field_encryption_key())
        else:
            self.stdout.write(generate_key())
