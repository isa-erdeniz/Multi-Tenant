"""
Plan limitleri ve FeatureUsage üzerinden aylık kullanım.
"""
from __future__ import annotations

from datetime import date
from typing import Optional

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from apps.subscriptions.models import FeatureUsage, Plan


def month_start(d: Optional[date] = None) -> date:
    d = d or timezone.now().date()
    return date(d.year, d.month, 1)


def get_effective_plan(user) -> Optional[Plan]:
    """Abonelikteki plan veya ücretsiz plan kaydı."""
    sub = getattr(user, "subscription", None)
    if sub and sub.plan_id:
        return sub.plan
    return Plan.objects.filter(slug="ucretsiz", is_active=True).first()


def _limit_for_feature(plan: Optional[Plan], feature_type: str) -> int:
    """0 = sınırsız. Plan yoksa ücretsiz varsayılanları."""
    defaults = {
        FeatureUsage.FEATURE_TRYON: 3,
        FeatureUsage.FEATURE_EDITOR: 5,
        FeatureUsage.FEATURE_STYLE_SESSION: 5,
        FeatureUsage.FEATURE_LOOK_CREATE: 5,
    }
    if not plan:
        return defaults.get(feature_type, 0)

    mapping = {
        FeatureUsage.FEATURE_TRYON: plan.tryon_limit,
        FeatureUsage.FEATURE_EDITOR: plan.editor_limit,
        FeatureUsage.FEATURE_STYLE_SESSION: plan.style_session_limit,
        FeatureUsage.FEATURE_LOOK_CREATE: plan.look_limit,
    }
    return int(mapping.get(feature_type, 0))


def get_usage(user, feature_type: str, m: Optional[date] = None) -> int:
    """Tenant bazlı aylık kullanım (aynı tenant üyeleri paylaşır)."""
    m = m or month_start()
    tid = getattr(user, "tenant_id", None)
    if not tid:
        return 0
    row = (
        FeatureUsage.objects.filter(
            tenant_id=tid, feature_type=feature_type, month=m
        )
        .only("count")
        .first()
    )
    return row.count if row else 0


def get_remaining(user, feature_type: str) -> Optional[int]:
    """
    Kalan kullanım; sınırsız ise None.
    Ücretsiz planda tryon_limit=0 → try-on kapalı (0 kalan).
    Diğer planlarda tryon_limit=0 → sınırsız sanal deneme.
    """
    plan = get_effective_plan(user)
    limit = _limit_for_feature(plan, feature_type)
    if (
        feature_type == FeatureUsage.FEATURE_TRYON
        and plan
        and plan.slug == "ucretsiz"
        and plan.tryon_limit == 0
    ):
        return 0
    if limit == 0:
        return None
    used = get_usage(user, feature_type)
    return max(0, limit - used)


def can_use_feature(user, feature_type: str) -> bool:
    if not user.is_authenticated:
        return False
    if not getattr(user, "tenant_id", None):
        return False

    sub = getattr(user, "subscription", None)
    if sub and sub.status == "trial" and sub.is_trial_expired():
        return False
    if sub and sub.status not in ("trial", "active"):
        return False

    remaining = get_remaining(user, feature_type)
    if remaining is None:
        return True
    return remaining > 0


@transaction.atomic
def increment_usage(user, feature_type: str, m: Optional[date] = None) -> FeatureUsage:
    m = m or month_start()
    tenant = getattr(user, "tenant", None)
    if tenant is None:
        raise ValueError("Kullanıcının tenant kaydı yok; kota artırılamaz.")
    obj, _ = FeatureUsage.objects.select_for_update().get_or_create(
        tenant=tenant,
        feature_type=feature_type,
        month=m,
        defaults={"count": 0, "user": user},
    )
    FeatureUsage.objects.filter(pk=obj.pk).update(count=F("count") + 1)
    obj.refresh_from_db(fields=["count"])
    return obj


def reset_monthly_usage_cleanup() -> int:
    """
    Geçmiş aylara ait kayıtları siler (isteğe bağlı bakım).
    Dönüş: silinen satır sayısı.
    """
    cutoff = month_start()
    deleted, _ = FeatureUsage.objects.filter(month__lt=cutoff).delete()
    return deleted
