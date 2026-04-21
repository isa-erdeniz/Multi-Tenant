from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from django.utils.text import slugify
from datetime import timedelta

from .models import DressifyeUser


@receiver(post_save, sender=DressifyeUser)
def create_user_subscription(sender, instance, created, **kwargs):
    """Yeni kullanıcıya kişisel Tenant + trial abonelik."""
    if created:
        from apps.tenants.models import Tenant
        from apps.subscriptions.models import UserSubscription, Plan

        email = (instance.email or "").strip()
        base = (slugify(email.split("@")[0] or "workspace") or "workspace")[:50]
        slug = f"{base}-u{instance.pk}"
        n = 0
        while Tenant.objects.filter(slug=slug).exists():
            n += 1
            slug = f"{base}-u{instance.pk}-{n}"

        tenant = Tenant.objects.create(
            name=email or instance.username or str(instance.pk),
            slug=slug,
            domain="",
            owner_user=instance,
            is_active=True,
        )
        DressifyeUser.objects.filter(pk=instance.pk).update(tenant_id=tenant.pk)

        free_plan = Plan.objects.filter(slug="ucretsiz").first()
        trial_end = timezone.now() + timedelta(days=7) if free_plan else None
        UserSubscription.objects.get_or_create(
            user_id=instance.pk,
            defaults={
                "plan": free_plan,
                "status": "trial",
                "end_date": trial_end,
                "tenant_id": tenant.pk,
            },
        )
        if trial_end and not instance.trial_end_date:
            DressifyeUser.objects.filter(pk=instance.pk).update(trial_end_date=trial_end)
