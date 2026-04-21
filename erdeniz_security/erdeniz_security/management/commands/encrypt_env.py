"""python manage.py encrypt_env / decrypt_env"""
import getpass
from pathlib import Path
from django.core.management.base import BaseCommand
from erdeniz_security.env_protector import EnvProtector
from erdeniz_security.audit import log_event


class Command(BaseCommand):
    help = ".env dosyasını şifreler (ErdenizVault)"

    def add_arguments(self, parser):
        parser.add_argument("--input", "-i", default=".env")
        parser.add_argument("--output", "-o", default=None)
        parser.add_argument("--project", "-p", default="")

    def handle(self, *args, **options):
        inp = Path(options["input"])
        if not inp.exists():
            self.stderr.write(self.style.ERROR(f"Dosya bulunamadı: {inp}"))
            return
        master = getpass.getpass("Master password: ")
        if not master:
            self.stderr.write(self.style.ERROR("Master password boş olamaz."))
            return
        try:
            out = EnvProtector(master).encrypt_env(inp, options["output"])
            log_event("ENV_ENCRYPT", str(inp), options["project"] or "default", success=True)
            self.stdout.write(self.style.SUCCESS(f"Şifrelendi: {out}"))
        except Exception as e:
            self.stderr.write(self.style.ERROR(str(e)))
