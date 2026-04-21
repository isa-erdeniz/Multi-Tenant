"""
Güçlü şifre üretici. İş ve kişisel kullanım için tek komut.
  python manage.py generate_password
  python manage.py generate_password --length 32 --no-symbols
  python manage.py generate_password --count 5
"""
from django.core.management.base import BaseCommand
from erdeniz_security.encryption import generate_password


class Command(BaseCommand):
    help = "Güçlü şifre üretir (CSPRNG)"

    def add_arguments(self, parser):
        parser.add_argument("--length", "-l", type=int, default=24)
        parser.add_argument("--no-symbols", action="store_true")
        parser.add_argument("--count", "-n", type=int, default=1)

    def handle(self, *args, **options):
        length = max(8, options["length"])
        symbols = not options["no_symbols"]
        count = max(1, min(20, options["count"]))
        for _ in range(count):
            pwd = generate_password(length=length, symbols=symbols)
            self.stdout.write(self.style.SUCCESS(pwd))
