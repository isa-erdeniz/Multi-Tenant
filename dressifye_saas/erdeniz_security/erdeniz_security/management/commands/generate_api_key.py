"""
API key üretme, listeleme, iptal ve döndürme.
  python manage.py generate_api_key --project mehlr --permissions read:all,write:query
  python manage.py generate_api_key --list
  python manage.py generate_api_key --list --project dressifye-saas
  python manage.py generate_api_key --revoke erd_a1b2
  python manage.py generate_api_key --rotate erd_a1b2
"""
from django.core.management.base import BaseCommand

from erdeniz_security.api_security import ErdenizAPIKeyManager


class Command(BaseCommand):
    help = "API key üret, listele, iptal veya döndür"

    def add_arguments(self, parser):
        parser.add_argument("--project", type=str, help="Proje adı (üretme için)")
        parser.add_argument("--permissions", type=str, default="", help="Virgülle ayrılmış izinler (örn: read:all,write:query)")
        parser.add_argument("--list", action="store_true", help="Aktif key'leri listele")
        parser.add_argument("--revoke", type=str, metavar="PREFIX", help="Key iptal et")
        parser.add_argument("--rotate", type=str, metavar="PREFIX", help="Key döndür (yeni üret)")

    def handle(self, *args, **options):
        mgr = ErdenizAPIKeyManager()
        if options["list"]:
            project = options.get("project")
            keys = mgr.list_api_keys(project)
            if not keys:
                self.stdout.write("Aktif API key yok.")
                return
            for k in keys:
                self.stdout.write(f"  {k['prefix']}  {k['project']}  {k['permissions']}  son kullanım: {k.get('usage_count', 0)}")
            return
        if options["revoke"]:
            prefix = options["revoke"]
            if mgr.revoke_api_key(prefix):
                self.stdout.write(self.style.SUCCESS(f"Key iptal edildi: {prefix}"))
            else:
                self.stderr.write(self.style.ERROR(f"Key bulunamadı veya zaten iptal: {prefix}"))
            return
        if options["rotate"]:
            prefix = options["rotate"]
            result = mgr.rotate_api_key(prefix)
            if result:
                new_prefix, full_key = result
                list_result = mgr.list_api_keys()
                obj = next((k for k in list_result if k["prefix"] == new_prefix), {})
                self._print_key_box("API Key Döndürüldü", obj.get("project", ""), new_prefix, full_key, str(obj.get("expires_at", "")), obj.get("permissions", []))
                self.stdout.write(self.style.WARNING("Eski key iptal edildi. Yeni key'i kaydedin."))
            else:
                self.stderr.write(self.style.ERROR(f"Key bulunamadı veya iptal: {prefix}"))
            return
        project = options.get("project")
        if not project:
            self.stderr.write(self.style.ERROR("--project gerekli (veya --list / --revoke / --rotate kullanın)."))
            return
        perms = [p.strip() for p in options.get("permissions", "").split(",") if p.strip()]
        prefix, full_key = mgr.create_api_key(project, perms or ["read:all"], 90)
        keys = mgr.list_api_keys(project)
        obj = next((k for k in keys if k["prefix"] == prefix), {})
        self._print_key_box("API Key Üretildi", project, prefix, full_key, str(obj.get("expires_at", "")), obj.get("permissions", perms or ["read:all"]))

    def _print_key_box(self, title: str, project: str, prefix: str, full_key: str, expires_str: str, permissions: list) -> None:
        perms_str = ", ".join(permissions)[:48] if permissions else "read:all"
        self.stdout.write("╔══════════════════════════════════════════════════════════╗")
        self.stdout.write(f"║  {title:<52} ║")
        self.stdout.write("╠══════════════════════════════════════════════════════════╣")
        self.stdout.write(f"║  Proje: {project[:44]:<44} ║")
        self.stdout.write(f"║  Prefix: {prefix:<46} ║")
        key_display = full_key[:48] + "..." if len(full_key) > 48 else full_key
        self.stdout.write(f"║  Key: {key_display:<48} ║")
        self.stdout.write(f"║  İzinler: {perms_str:<44} ║")
        self.stdout.write(f"║  Son kullanma: {str(expires_str)[:38]:<38} ║")
        self.stdout.write("╠══════════════════════════════════════════════════════════╣")
        self.stdout.write("║  ⚠️  BU KEY SADECE 1 KEZ GÖSTERİLİR. KAYDEDIN!         ║")
        self.stdout.write("╚══════════════════════════════════════════════════════════╝")