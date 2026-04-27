"""
Ödeme sonrası abonelik güncellemeleri (callback + webhook).
"""
import logging
from datetime import timedelta

from django.utils import timezone

from apps.profiles.models import UserProfile
from apps.subscriptions.models import Plan, UserSubscription

logger = logging.getLogger(__name__)


def activate_subscription(user, plan: Plan | None, period: str) -> None:
    """
    Checkout callback: yeni ödeme veya plan değişimi.
    Aktif/deneme + farklı plan ise kalan süreyi yeni döneme ekler.
    """
    if not plan:
        return
    tid = getattr(user, "tenant_id", None)
    if not tid:
        logger.error("activate_subscription: user %s için tenant yok", user.pk)
        return
    sub, created = UserSubscription.objects.get_or_create(
        user=user,
        defaults={"tenant_id": tid},
    )
    if not created and sub.tenant_id != tid:
        sub.tenant_id = tid
    now = timezone.now()
    delta = timedelta(days=365 if period == "yearly" else 30)

    if (
        sub.plan_id
        and sub.plan_id != plan.id
        and sub.status in ("active", "trial")
        and sub.end_date
        and sub.end_date > now
    ):
        remaining = sub.end_date - now
        sub.end_date = now + delta + remaining
    else:
        sub.end_date = now + delta

    sub.plan = plan
    sub.status = "active"
    sub.save()
    logger.info("%s → %s aktif (%s)", user.email, plan.slug, period)


def extend_subscription_renewal(user, plan: Plan | None, period: str) -> None:
    """
    Webhook / otomatik yenileme: mevcut bitişten itibaren uzatır.
    """
    if not plan:
        return
    tid = getattr(user, "tenant_id", None)
    if not tid:
        logger.error("extend_subscription_renewal: user %s için tenant yok", user.pk)
        return
    sub, created = UserSubscription.objects.get_or_create(
        user=user,
        defaults={"tenant_id": tid},
    )
    if not created and sub.tenant_id != tid:
        sub.tenant_id = tid
    now = timezone.now()
    delta = timedelta(days=365 if period == "yearly" else 30)
    base = sub.end_date if sub.end_date and sub.end_date > now else now
    sub.end_date = base + delta
    sub.plan = plan
    sub.status = "active"
    sub.save()
    logger.info("%s yenileme uzatıldı → %s (%s)", user.email, plan.slug, period)


def apply_dressifye_subscription_entitlements(
    user,
    *,
    plan: Plan | None,
    tier: str,
    custom_title: str,
    subscription_ref: str,
    customer_ref: str,
    period: str = "monthly",
) -> None:
    """
    Dressifye abonelik callback: dressifye_saas planı + profil ünvanı / özellik bayrakları.
    """
    if plan:
        activate_subscription(user, plan, period)
    tier_norm = (tier or "").lower()
    profile, _ = UserProfile.objects.get_or_create(user=user)
    profile.dressifye_marketing_tier = tier_norm
    profile.dressifye_display_title = (custom_title or "")[:120]
    profile.feature_voice_ai = tier_norm in ("platinum", "diamond")
    profile.feature_white_label_reports = tier_norm == "diamond"
    profile.save(
        update_fields=[
            "dressifye_marketing_tier",
            "dressifye_display_title",
            "feature_voice_ai",
            "feature_white_label_reports",
        ]
    )
    sub = getattr(user, "subscription", None)
    if sub and (subscription_ref or customer_ref):
        fields = []
        if subscription_ref:
            sub.iyzico_subscription_ref = subscription_ref[:200]
            fields.append("iyzico_subscription_ref")
        if customer_ref:
            sub.iyzico_customer_ref = customer_ref[:200]
            fields.append("iyzico_customer_ref")
        if fields:
            sub.save(update_fields=fields)
    logger.info(
        "dressifye entitlements: %s tier=%s title=%r",
        user.email,
        tier_norm,
        profile.dressifye_display_title,
    )
