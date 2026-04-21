"""
python manage.py clear_old_conversations
python manage.py clear_old_conversations --days 30
python manage.py clear_old_conversations --project looopone
python manage.py clear_old_conversations --empty-only
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from mehlr.models import Conversation


class Command(BaseCommand):
    help = "Eski veya boş konuşmaları temizler."

    def add_arguments(self, parser):
        parser.add_argument(
            "--days", type=int, default=90,
            help="Bu kadar günden eski konuşmaları sil. (varsayılan: 90)"
        )
        parser.add_argument(
            "--project", type=str, default=None,
            help="Sadece belirli proje slug'ı için sil."
        )
        parser.add_argument(
            "--empty-only", action="store_true",
            help="Sadece mesajsız konuşmaları sil."
        )
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Silmeden önizleme yap."
        )

    def handle(self, *args, **options):
        days        = options["days"]
        project     = options["project"]
        empty_only  = options["empty_only"]
        dry_run     = options["dry_run"]

        cutoff = timezone.now() - timedelta(days=days)
        qs = Conversation.objects.filter(created_at__lt=cutoff)

        if project:
            qs = qs.filter(project__slug=project)

        if empty_only:
            qs = qs.filter(messages__isnull=True).distinct()

        count = qs.count()

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"[DRY-RUN] Silinecek konuşma sayısı: {count} "
                    f"(>{days}d, proje={project or 'hepsi'}, boş-sadece={empty_only})"
                )
            )
            return

        if count == 0:
            self.stdout.write(self.style.SUCCESS("Silinecek konuşma yok."))
            return

        confirm = input(f"{count} konuşma silinecek. Onaylıyor musunuz? (evet/hayır): ")
        if confirm.lower() != "evet":
            self.stdout.write(self.style.WARNING("İptal edildi."))
            return

        deleted, _ = qs.delete()
        self.stdout.write(
            self.style.SUCCESS(f"✅ {deleted} konuşma silindi.")
        )
