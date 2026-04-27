"""
Abonelik yaşam döngüsü — plan değişiminde harici AI kullanım sayaçlarına dokunulmaz.
"""

from __future__ import annotations

import logging

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from apps.subscriptions.models import UserSubscription

logger = logging.getLogger(__name__)


@receiver(pre_save, sender=UserSubscription)
def usersubscription_cache_plan(sender, instance: UserSubscription, **kwargs) -> None:
    """Plan yükseltmesi / değişiminde önceki plan_id'yi saklar."""
    if instance._state.adding or not instance.pk:
        instance._sub_prev_plan_id = None
        return
    try:
        prior = UserSubscription.objects.get(pk=instance.pk)
        instance._sub_prev_plan_id = prior.plan_id
    except UserSubscription.DoesNotExist:
        instance._sub_prev_plan_id = None


@receiver(post_save, sender=UserSubscription)
def usersubscription_plan_changed_log(sender, instance: UserSubscription, created: bool, **kwargs) -> None:
    """
    Plan değiştiğinde `ai_credits_used` ve günlükler korunur; yeni limit anında geçerli olur.

    Aylık sıfırlama yalnızca `QuotaManager._ensure_ai_period` ile takvim döneminde yapılır.
    """
    if created:
        return
    prev = getattr(instance, "_sub_prev_plan_id", None)
    if prev is not None and prev != instance.plan_id:
        logger.info(
            "subscription_plan_changed user_id=%s tenant_id=%s plan_id %s -> %s "
            "(ai_credits_used=%s unchanged)",
            instance.user_id,
            instance.tenant_id,
            prev,
            instance.plan_id,
            instance.ai_credits_used,
        )
