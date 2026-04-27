"""
python manage.py seed_projects

PROJECT_PROMPTS'taki projeleri DB'ye yükler.
Varsa günceller, yoksa oluşturur (upsert).
"""
from django.core.management.base import BaseCommand
from mehlr.models import Project
from mehlr.prompts.project_prompts import PROJECT_PROMPTS


class Command(BaseCommand):
    help = "PROJECT_PROMPTS'taki tüm projeleri DB'ye seed eder (upsert)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run", action="store_true",
            help="DB'ye yazmadan önizleme yap."
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        created_count = updated_count = 0

        for slug, meta in PROJECT_PROMPTS.items():
            # dressifye-saas → dressifye_saas slug normalize (DB slug field)
            db_slug = slug.replace("-", "_")
            display = meta.get("display_name", slug.title())
            description = meta.get("description", "")
            if not description:
                description = meta.get("system_prompt", "")[:500] or f"Proje: {display}"
            api_endpoint = meta.get("website", "")
            if api_endpoint == "placeholder":
                api_endpoint = ""
            project_type = meta.get("domain", "mehlr")
            context_prompt = meta.get("system_prompt", "") or description

            if dry_run:
                self.stdout.write(
                    self.style.WARNING(f"[DRY-RUN] {db_slug} — {display}")
                )
                continue

            obj, created = Project.objects.update_or_create(
                slug=db_slug,
                defaults={
                    "name": display,
                    "description": description[:500],
                    "project_type": project_type,
                    "context_prompt": context_prompt[:2000],
                    "api_endpoint": api_endpoint,
                    "is_active": True,
                },
            )

            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f"✅ Oluşturuldu: {db_slug}"))
            else:
                updated_count += 1
                self.stdout.write(self.style.HTTP_INFO(f"♻️  Güncellendi: {db_slug}"))

        if not dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f"\nTamamlandı — {created_count} oluşturuldu, {updated_count} güncellendi."
                )
            )
