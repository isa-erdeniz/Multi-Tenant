"""
Model sinyalleri — durum geçişleri ve bildirim kuyruğu.
"""

from __future__ import annotations

import logging

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from apps.ai_integrations.models import AIProcessingTask

logger = logging.getLogger(__name__)


@receiver(pre_save, sender=AIProcessingTask)
def ai_task_cache_status(sender, instance: AIProcessingTask, **kwargs) -> None:
    """Durum geçişlerini post_save için önbelleğe alır."""
    if instance._state.adding or not instance.pk:
        instance._ai_old_status = None
        return
    try:
        prev = AIProcessingTask.all_objects.get(pk=instance.pk)
        instance._ai_old_status = prev.status
    except AIProcessingTask.DoesNotExist:
        instance._ai_old_status = None


@receiver(post_save, sender=AIProcessingTask)
def ai_task_after_save(sender, instance: AIProcessingTask, created: bool, **kwargs) -> None:
    """Durum değişimlerini günlükler; terminal durumda bildirim görevi tetikler."""
    if created:
        logger.info("AI task created id=%s tenant=%s", instance.pk, instance.tenant_id)
        return
    old = getattr(instance, "_ai_old_status", None)
    if old is not None and old != instance.status:
        logger.info(
            "AI task status transition id=%s %s -> %s tenant=%s",
            instance.pk,
            old,
            instance.status,
            instance.tenant_id,
        )
    if instance.is_terminal_status:
        from apps.ai_integrations.tasks import notify_task_completion

        notify_task_completion.delay(instance.pk)
