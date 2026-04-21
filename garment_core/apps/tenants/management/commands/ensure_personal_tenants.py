"""
Tenant'ı olmayan kullanıcılar için kişisel Tenant + abonelik tenant_id atar.
Sinyal dışı oluşturulan hesaplar (import, eski veri) için çalıştırın.
"""
from django.core.management.base import BaseCommand
from django.utils.text import slugify

from apps.accounts.models import DressifyeUser
from apps.subscriptions.models import UserSubscription
from apps.tenants.models import Tenant


class Command(BaseCommand):
    help = "tenant_id boş kullanıcılar için Tenant oluşturur ve aboneliği bağlar."

    def handle(self, *args, **options):
        n_t = 0
        n_s = 0
        for u in DressifyeUser.objects.filter(tenant_id__isnull=True).iterator():
            email = (u.email or "").strip()
            base = (slugify(email.split("@")[0] or "workspace") or "workspace")[:50]
            slug = f"{base}-u{u.pk}"
            i = 0
            while Tenant.objects.filter(slug=slug).exists():
                i += 1
                slug = f"{base}-u{u.pk}-{i}"
            t = Tenant.objects.create(
                name=email or u.username or str(u.pk),
                slug=slug,
                domain="",
                owner_user=u,
                is_active=True,
            )
            DressifyeUser.objects.filter(pk=u.pk).update(tenant_id=t.id)
            n_t += 1
            updated = UserSubscription.objects.filter(user_id=u.pk, tenant_id__isnull=True).update(
                tenant_id=t.id
            )
            n_s += updated
        self.stdout.write(
            self.style.SUCCESS(
                f"Tamam: {n_t} tenant oluşturuldu, {n_s} abonelik güncellendi."
            )
        )
