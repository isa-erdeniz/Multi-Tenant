"""
python manage.py generate_test_env
python manage.py generate_test_env --project dressifye_saas
python manage.py generate_test_env --all-projects
python manage.py generate_test_env --output /custom/path/.env
python manage.py generate_test_env --overwrite
"""

from pathlib import Path

from django.core.management.base import BaseCommand

from erdeniz_security.encryption import (
    generate_field_encryption_key,
    generate_key,
    generate_password,
)

PROJECTS = [
    "looopone_dashboard",
    "worktrackere",
    "dressifye_saas",
    "hairinfinitye",
    "edulingoe",
    "stylecoree",
    "drivetrackere",
    "dressifye",
    "mehlr_1_0",
]

ENV_TEMPLATE = """\
# ╔══════════════════════════════════════════════════════════╗
# ║     ErdenizTech — {project} Test Ortamı .env            ║
# ║     Otomatik üretildi: {timestamp}                       ║
# ║     UYARI: Bu dosyayı git'e commit ETME!                 ║
# ╚══════════════════════════════════════════════════════════╝

# ─── Django Core ──────────────────────────────────────────
SECRET_KEY={secret_key}
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0

# ─── Veritabanı ───────────────────────────────────────────
DATABASE_URL=sqlite:///db_test_{project}.sqlite3
DATABASE_NAME=db_test_{project}
DATABASE_USER=erdeniz_test
DATABASE_PASSWORD={db_password}
DATABASE_HOST=localhost
DATABASE_PORT=5432

# ─── ErdenizTech Şifreleme ────────────────────────────────
ERDENIZ_ENCRYPTION_KEY={encryption_key}
FIELD_ENCRYPTION_KEY={field_encryption_key}

# ─── JWT & API Güvenlik ───────────────────────────────────
REQUEST_SIGNING_SECRET={signing_secret}
JWT_SECRET_KEY={jwt_secret}

# ─── Webhook Secrets ──────────────────────────────────────
WEBHOOK_SECRET={webhook_secret}
WEBHOOK_IYZICO_SECRET={iyzico_secret}
WEBHOOK_STRIPE_SECRET={stripe_secret}

# ─── Cache / Redis ────────────────────────────────────────
CACHE_URL=redis://localhost:6379/0
REDIS_URL=redis://localhost:6379/0

# ─── Email (test) ─────────────────────────────────────────
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=test@erdeniztech.com
EMAIL_HOST_PASSWORD={email_password}
EMAIL_USE_TLS=True

# ─── Proje Kimliği ────────────────────────────────────────
ERDENIZ_PROJECT_ID={project}

# ─── Google / AI (isteğe bağlı) ───────────────────────────
GOOGLE_API_KEY=
GEMINI_API_KEY=
OPENAI_API_KEY=

# ─── Celery ───────────────────────────────────────────────
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# ─── Sentry (isteğe bağlı) ────────────────────────────────
SENTRY_DSN=
"""


class Command(BaseCommand):
    help = "Test ortamı için .env dosyasını otomatik oluştur"

    def add_arguments(self, parser):
        parser.add_argument("--project", "-p", type=str, default="erdeniz_security")
        parser.add_argument("--output", "-o", type=str, default=None)
        parser.add_argument("--all-projects", action="store_true")
        parser.add_argument("--overwrite", action="store_true")
        parser.add_argument("--silent", action="store_true")

    def handle(self, *args, **options):
        if options["all_projects"]:
            import os

            root = os.environ.get("ERDENIZTECH_ROOT", str(Path.home() / "erdeniztech"))
            for project in PROJECTS:
                project_dir = Path(root) / project
                if project_dir.exists():
                    self._generate_env(
                        project=project,
                        output_path=project_dir / ".env",
                        overwrite=options["overwrite"],
                        silent=options["silent"],
                    )
                else:
                    if not options["silent"]:
                        self.stdout.write(
                            self.style.WARNING(f"Atlandı: {project_dir} bulunamadı")
                        )
            return

        output = options["output"] or ".env"
        self._generate_env(
            project=options["project"],
            output_path=Path(output),
            overwrite=options["overwrite"],
            silent=options["silent"],
        )

    def _generate_env(
        self, project: str, output_path: Path, overwrite: bool, silent: bool
    ):
        from datetime import datetime

        if output_path.exists() and not overwrite:
            if not silent:
                self.stdout.write(
                    self.style.WARNING(
                        f"⚠️  {output_path} zaten var. Üzerine yazmak için --overwrite kullan."
                    )
                )
            return

        content = ENV_TEMPLATE.format(
            project=project,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            secret_key="django-insecure-test-"
            + generate_password(40, symbols=False),
            db_password=generate_password(16, symbols=False),
            encryption_key=generate_key(),
            field_encryption_key=generate_field_encryption_key(),
            signing_secret=generate_password(32, symbols=False),
            jwt_secret=generate_password(48, symbols=False),
            webhook_secret=generate_password(32, symbols=False),
            iyzico_secret=generate_password(32, symbols=False),
            stripe_secret=generate_password(32, symbols=False),
            email_password=generate_password(16, symbols=False),
        )

        output_path.write_text(content, encoding="utf-8")

        # .env.example da oluştur (değerler olmadan, sadece key'ler)
        example_path = output_path.parent / ".env.example"
        if not example_path.exists():
            example_lines = []
            for line in content.splitlines():
                if "=" in line and not line.startswith("#"):
                    key = line.split("=")[0]
                    example_lines.append(f"{key}=")
                else:
                    example_lines.append(line)
            example_path.write_text("\n".join(example_lines), encoding="utf-8")

        if not silent:
            self._print_success_box(project, output_path)

        # Audit log
        try:
            from erdeniz_security.audit import log_event

            log_event(
                "CONFIG_CHANGE",
                str(output_path),
                project,
                success=True,
                details={"action": "generate_test_env"},
            )
        except Exception:
            pass

    def _print_success_box(self, project: str, output_path: Path):
        self.stdout.write("")
        self.stdout.write(
            "╔══════════════════════════════════════════════════════════╗"
        )
        self.stdout.write(
            "║        ErdenizTech — Test .env Oluşturuldu              ║"
        )
        self.stdout.write(
            "╠══════════════════════════════════════════════════════════╣"
        )
        self.stdout.write(f"║  Proje    : {project:<44} ║")
        self.stdout.write(f"║  Dosya    : {str(output_path):<44} ║")
        self.stdout.write(
            "╠══════════════════════════════════════════════════════════╣"
        )
        self.stdout.write(
            "║  ✅ SECRET_KEY          → üretildi                      ║"
        )
        self.stdout.write(
            "║  ✅ ERDENIZ_ENCRYPTION_KEY → üretildi                   ║"
        )
        self.stdout.write(
            "║  ✅ FIELD_ENCRYPTION_KEY   → üretildi                   ║"
        )
        self.stdout.write(
            "║  ✅ REQUEST_SIGNING_SECRET → üretildi                   ║"
        )
        self.stdout.write(
            "║  ✅ JWT_SECRET_KEY          → üretildi                  ║"
        )
        self.stdout.write(
            "║  ✅ WEBHOOK_SECRET          → üretildi                   ║"
        )
        self.stdout.write(
            "║  ✅ .env.example            → oluşturuldu               ║"
        )
        self.stdout.write(
            "╠══════════════════════════════════════════════════════════╣"
        )
        self.stdout.write(
            "║  ⚠️  .env dosyasını git'e commit ETME!                  ║"
        )
        self.stdout.write(
            "║  ⚠️  Production için değerleri manuel değiştir!         ║"
        )
        self.stdout.write(
            "╚══════════════════════════════════════════════════════════╝"
        )
        self.stdout.write("")
        self.stdout.write("  Sonraki adımlar:")
        self.stdout.write("  1. python manage.py migrate")
        self.stdout.write("  2. python manage.py security_check")
        self.stdout.write("  3. pytest erdeniz_security/tests/")
        self.stdout.write("")
