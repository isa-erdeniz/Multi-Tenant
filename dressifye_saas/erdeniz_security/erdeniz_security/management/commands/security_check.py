"""python manage.py security_check [--all-projects] [--fix]"""
import os
from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Güvenlik denetimi (ErdenizTech)"

    def add_arguments(self, parser):
        parser.add_argument("--project", type=str, default=None)
        parser.add_argument("--all-projects", action="store_true")
        parser.add_argument("--fix", action="store_true")

    def _checks(self, project_name: str) -> tuple[dict, list[str]]:
        r = {"critical": {"pass": 0, "fail": 0}, "high": {"pass": 0, "fail": 0}, "medium": {"pass": 0, "fail": 0}, "info": {"pass": 0, "fail": 0}}
        failed = []
        sk = os.environ.get("SECRET_KEY") or getattr(settings, "SECRET_KEY", "")
        if sk and "insecure" not in str(sk).lower() and len(sk) >= 32:
            r["critical"]["pass"] += 1
        else:
            r["critical"]["fail"] += 1
            failed.append("[CRITICAL] SECRET_KEY env'de ve güçlü olmalı")
        if not getattr(settings, "DEBUG", True):
            r["critical"]["pass"] += 1
        else:
            r["critical"]["fail"] += 1
            failed.append("[CRITICAL] DEBUG=False (production)")
        if os.environ.get("FIELD_ENCRYPTION_KEY"):
            r["critical"]["pass"] += 1
        else:
            r["critical"]["fail"] += 1
            failed.append("[CRITICAL] FIELD_ENCRYPTION_KEY tanımlı olmalı")
        if os.environ.get("DATABASE_PASSWORD") or (getattr(settings, "DATABASES", {}).get("default", {}).get("PASSWORD")):
            r["critical"]["pass"] += 1
        else:
            r["critical"]["fail"] += 1
            failed.append("[CRITICAL] Veritabanı şifresi env'de olmalı")
        try:
            if ".env" in open(".gitignore").read():
                r["critical"]["pass"] += 1
            else:
                r["critical"]["fail"] += 1
                failed.append("[CRITICAL] .env .gitignore'da olmalı")
        except FileNotFoundError:
            r["critical"]["fail"] += 1
            failed.append("[CRITICAL] .gitignore yok")
        hashers = getattr(settings, "PASSWORD_HASHERS", [])
        if hashers and "Argon2" in str(hashers[0]):
            r["high"]["pass"] += 1
        else:
            r["high"]["fail"] += 1
            failed.append("[HIGH] Argon2 birincil olmalı")
        if getattr(settings, "SESSION_COOKIE_SECURE", False):
            r["high"]["pass"] += 1
        else:
            r["high"]["fail"] += 1
        if getattr(settings, "CSRF_COOKIE_SECURE", False):
            r["high"]["pass"] += 1
        else:
            r["high"]["fail"] += 1
        if getattr(settings, "SECURE_SSL_REDIRECT", False):
            r["high"]["pass"] += 1
        else:
            r["high"]["fail"] += 1
        if "axes" in getattr(settings, "INSTALLED_APPS", []):
            r["high"]["pass"] += 1
        else:
            r["high"]["fail"] += 1
        if getattr(settings, "SECURE_HSTS_SECONDS", 0) >= 31536000:
            r["medium"]["pass"] += 1
        else:
            r["medium"]["fail"] += 1
        if getattr(settings, "X_FRAME_OPTIONS", "") == "DENY":
            r["medium"]["pass"] += 1
        else:
            r["medium"]["fail"] += 1
        if "erdeniz_security" in getattr(settings, "INSTALLED_APPS", []):
            r["medium"]["pass"] += 1
        else:
            r["medium"]["fail"] += 1
        # Hafta 2 — API & ağ
        rf = getattr(settings, "REST_FRAMEWORK", None)
        if rf and isinstance(rf, dict):
            r["critical"]["pass"] += 1
        else:
            r["critical"]["fail"] += 1
            failed.append("[CRITICAL] REST_FRAMEWORK ayarları tanımlı olmalı")
        try:
            from datetime import timedelta
            jwt = getattr(settings, "SIMPLE_JWT", {})
            access = jwt.get("ACCESS_TOKEN_LIFETIME") or timedelta(minutes=15)
            if getattr(access, "total_seconds", lambda: 900)() <= 900:
                r["critical"]["pass"] += 1
            else:
                r["critical"]["fail"] += 1
                failed.append("[CRITICAL] JWT access token süresi ≤15 dakika olmalı")
        except Exception:
            r["critical"]["fail"] += 1
            failed.append("[CRITICAL] SIMPLE_JWT (erdeniz_security.api_security.ERDENIZ_JWT_SETTINGS) tanımlı olmalı")
        if os.environ.get("REQUEST_SIGNING_SECRET") or getattr(settings, "REQUEST_SIGNING_SECRET", ""):
            r["critical"]["pass"] += 1
        else:
            r["critical"]["fail"] += 1
            failed.append("[CRITICAL] REQUEST_SIGNING_SECRET tanımlı olmalı")
        cors_origins = getattr(settings, "CORS_ALLOWED_ORIGINS", []) or []
        if cors_origins and "*" not in str(cors_origins):
            r["high"]["pass"] += 1
        else:
            r["high"]["fail"] += 1
            failed.append("[HIGH] CORS origin'leri kısıtlı olmalı (wildcard yok)")
        if rf and (rf.get("DEFAULT_THROTTLE_CLASSES") or rf.get("DEFAULT_THROTTLE_RATES")):
            r["high"]["pass"] += 1
        else:
            r["high"]["fail"] += 1
            failed.append("[HIGH] API rate limiting aktif olmalı")
        if "rest_framework_simplejwt.token_blacklist" in getattr(settings, "INSTALLED_APPS", []):
            r["high"]["pass"] += 1
        else:
            r["high"]["fail"] += 1
            failed.append("[HIGH] Token blacklist (rest_framework_simplejwt.token_blacklist) ekli olmalı")
        r["info"]["pass"] += 1 if os.path.isfile(".env.example") else 0
        if not os.path.isfile(".env.example"):
            r["info"]["fail"] += 1
        return r, failed

    def _score(self, r: dict) -> int:
        total = 50
        for level, w in [("critical", 10), ("high", 5), ("medium", 3), ("info", 1)]:
            total += r[level]["pass"] * w
            total -= r[level]["fail"] * (w + 2)
        return max(0, min(100, total))

    def handle(self, *args, **options):
        if options["all_projects"]:
            self.stdout.write("ErdenizTech — Toplu Güvenlik Raporu")
            self.stdout.write("Her proje klasöründe 'python manage.py security_check' çalıştırın.")
            return
        project_name = options["project"] or "current"
        r, failed = self._checks(project_name)
        score = self._score(r)
        self.stdout.write("╔══════════════════════════════════════════╗")
        self.stdout.write("║     ErdenizTech Güvenlik Denetim Raporu   ║")
        self.stdout.write(f"║     Proje: {project_name[:28]:<28} ║")
        self.stdout.write("╠══════════════════════════════════════════╣")
        self.stdout.write(f"║  CRITICAL:  {r['critical']['pass']} geçti / {r['critical']['fail']} başarısız")
        self.stdout.write(f"║  HIGH:      {r['high']['pass']} geçti / {r['high']['fail']} başarısız")
        self.stdout.write(f"║  MEDIUM:    {r['medium']['pass']} geçti / {r['medium']['fail']} başarısız")
        self.stdout.write(f"║  INFO:      {r['info']['pass']} geçti / {r['info']['fail']} başarısız")
        self.stdout.write("╠══════════════════════════════════════════╣")
        label = "MÜKEMMEL" if score >= 90 else "İYİ" if score >= 70 else "GELİŞTİRİLMELİ"
        self.stdout.write(f"║  Skor: {score}/100  {label}")
        self.stdout.write("╚══════════════════════════════════════════╝")
        for msg in failed:
            self.stdout.write(self.style.WARNING(msg))
        if options["fix"]:
            self.stdout.write("--fix: Ayarları manuel güncelleyin.")
