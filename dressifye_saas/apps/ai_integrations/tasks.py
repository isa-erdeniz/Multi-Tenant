"""
Celery görevleri: harici AI işlem hattı ve periyodik bakım.
"""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from billiard.exceptions import SoftTimeLimitExceeded
from celery import shared_task
from django.db import transaction
from django.utils import timezone

from apps.ai_integrations.exceptions import (
    AIProviderError,
    ProviderRateLimitError,
    ProviderUnavailableError,
    QuotaExceededError,
)
from apps.ai_integrations.models import AIProcessingTask
from apps.ai_integrations.services import (
    ProviderFactory,
    QuotaManager,
    attach_failure_context,
    enforce_provider_rate_limit,
    run_provider_check_status,
    run_provider_process_with_fallback,
    run_provider_validate_and_estimate,
)

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    soft_time_limit=300,
    time_limit=360,
)
def process_ai_task(self, task_id: int) -> dict[str, Any]:
    """
    Kuyruktaki bir AI işini işler.

    Args:
        task_id: AIProcessingTask birincil anahtarı.

    Returns:
        Özet sözlük: ``status`` / ``provider_used`` veya hata ``result`` kodu.
    """
    task = (
        AIProcessingTask.all_objects.select_related("provider", "tenant", "user")
        .filter(pk=task_id)
        .first()
    )
    if task is None:
        logger.error(
            "process_ai_task: task bulunamadı",
            extra={"ai_event": "task_missing", "ai_task_id": task_id},
        )
        return {"result": "missing", "ai_task_id": task_id}

    if task.status != AIProcessingTask.STATUS_QUEUED:
        return {"result": "skip", "status": task.status, "ai_task_id": task_id}

    if task.user_id is None:
        task.status = AIProcessingTask.STATUS_FAILED
        task.error_message = "user is required for quota"
        task.completed_at = timezone.now()
        task.save(update_fields=["status", "error_message", "completed_at", "updated_at"])
        return {"result": "no-user", "ai_task_id": task_id}

    credits_charged = 0
    try:
        provider_impl, estimated = run_provider_validate_and_estimate(task)
        task.estimated_credits = estimated
        task.save(update_fields=["estimated_credits", "updated_at"])
        enforce_provider_rate_limit(task.provider)
        QuotaManager.check_quota(task.tenant_id, task.user, estimated)

        with transaction.atomic():
            QuotaManager.deduct_credits(task.tenant_id, task.user, estimated, task)
            credits_charged = estimated
            task.credits_used = estimated
            task.status = AIProcessingTask.STATUS_PROCESSING
            task.started_at = timezone.now()
            task.error_message = ""
            task.save(
                update_fields=[
                    "credits_used",
                    "status",
                    "started_at",
                    "error_message",
                    "updated_at",
                ]
            )

        result, provider_used = run_provider_process_with_fallback(provider_impl, task)
        ext_id = str(result.get("external_task_id") or "")
        out = dict(task.output_data or {})
        if result.get("raw") is not None:
            out["provider_response_raw"] = result.get("raw")
        task.external_task_id = ext_id
        task.output_data = out
        task.save(update_fields=["external_task_id", "output_data", "updated_at"])

        state = str(result.get("status") or "").lower()
        if state in {"completed", "succeeded", "done"}:
            task.status = AIProcessingTask.STATUS_COMPLETED
            task.completed_at = timezone.now()
            task.save(update_fields=["status", "completed_at", "updated_at"])
        logger.info(
            "process_ai_task tamamlandı",
            extra={
                "ai_event": "process_done",
                "ai_task_id": task.pk,
                "ai_provider_used": provider_used,
                "ai_status": task.status,
            },
        )
        return {
            "status": task.status,
            "provider_used": provider_used,
            "ai_task_id": task.pk,
        }

    except QuotaExceededError as exc:
        logger.warning(
            "process_ai_task kota aşımı",
            extra={
                "ai_event": "quota_exceeded",
                "ai_task_id": task_id,
                "ai_required": getattr(exc, "required", None),
            },
        )
        task.status = AIProcessingTask.STATUS_FAILED
        task.error_message = str(exc)[:2000]
        task.completed_at = timezone.now()
        attach_failure_context(task, exc)
        task.save(
            update_fields=[
                "output_data",
                "status",
                "error_message",
                "completed_at",
                "updated_at",
            ]
        )
        return {"result": "quota_exceeded", "ai_task_id": task_id}

    except SoftTimeLimitExceeded:
        logger.error(
            "process_ai_task soft time limit",
            extra={"ai_event": "soft_time_limit", "ai_task_id": task_id},
        )
        if credits_charged:
            QuotaManager.refund_credits(task, reason="soft_time_limit")
        task.credits_used = 0
        task.status = AIProcessingTask.STATUS_FAILED
        task.error_message = "soft_time_limit"
        task.completed_at = timezone.now()
        attach_failure_context(task, RuntimeError("SoftTimeLimitExceeded"))
        task.save(
            update_fields=[
                "output_data",
                "status",
                "error_message",
                "completed_at",
                "credits_used",
                "updated_at",
            ]
        )
        raise

    except ProviderRateLimitError as exc:
        logger.warning(
            "process_ai_task rate limited",
            extra={"ai_event": "rate_limited", "ai_task_id": task_id},
        )
        if credits_charged:
            QuotaManager.refund_credits(task, reason="rate_limit_retry")
        task.credits_used = 0
        attach_failure_context(task, exc)
        task.retry_count = min(255, (task.retry_count or 0) + 1)
        if int(self.request.retries) >= int(self.max_retries):
            task.status = AIProcessingTask.STATUS_FAILED
            task.error_message = "max_retries_rate_limit"
            task.completed_at = timezone.now()
            task.save(
                update_fields=[
                    "output_data",
                    "status",
                    "error_message",
                    "completed_at",
                    "credits_used",
                    "retry_count",
                    "updated_at",
                ]
            )
            return {"result": "max_retries", "reason": "rate_limit", "ai_task_id": task_id}
        task.status = AIProcessingTask.STATUS_QUEUED
        task.started_at = None
        task.error_message = ""
        task.save(
            update_fields=[
                "output_data",
                "status",
                "started_at",
                "error_message",
                "credits_used",
                "retry_count",
                "updated_at",
            ]
        )
        countdown = max(1, int(getattr(exc, "retry_after", None) or 60))
        raise self.retry(exc=exc, countdown=countdown) from exc

    except ProviderUnavailableError as exc:
        logger.warning(
            "process_ai_task provider unavailable",
            extra={"ai_event": "provider_unavailable", "ai_task_id": task_id},
        )
        if credits_charged:
            QuotaManager.refund_credits(task, reason="provider_unavailable_retry")
        task.credits_used = 0
        attach_failure_context(task, exc)
        task.retry_count = min(255, (task.retry_count or 0) + 1)
        if int(self.request.retries) >= int(self.max_retries):
            task.status = AIProcessingTask.STATUS_FAILED
            task.error_message = "max_retries_provider_unavailable"
            task.completed_at = timezone.now()
            task.save(
                update_fields=[
                    "output_data",
                    "status",
                    "error_message",
                    "completed_at",
                    "credits_used",
                    "retry_count",
                    "updated_at",
                ]
            )
            return {"result": "max_retries", "reason": "provider_unavailable", "ai_task_id": task_id}
        task.status = AIProcessingTask.STATUS_QUEUED
        task.started_at = None
        task.error_message = ""
        task.save(
            update_fields=[
                "output_data",
                "status",
                "started_at",
                "error_message",
                "credits_used",
                "retry_count",
                "updated_at",
            ]
        )
        rc = int(task.retry_count or 0)
        countdown = 60 * (2 ** min(rc, 10))
        raise self.retry(exc=exc, countdown=countdown) from exc

    except AIProviderError as exc:
        logger.warning(
            "process_ai_task failed",
            extra={
                "ai_event": "provider_error",
                "ai_task_id": task_id,
                "ai_error": str(exc)[:500],
            },
            exc_info=logger.isEnabledFor(logging.DEBUG),
        )
        if credits_charged:
            QuotaManager.refund_credits(task, reason=str(exc)[:500])
        task.credits_used = 0
        task.status = AIProcessingTask.STATUS_FAILED
        task.error_message = str(exc)[:2000]
        task.completed_at = timezone.now()
        attach_failure_context(task, exc)
        task.save(
            update_fields=[
                "output_data",
                "status",
                "error_message",
                "completed_at",
                "credits_used",
                "updated_at",
            ]
        )
        return {"result": "failed", "ai_task_id": task_id}

    except Exception as exc:
        logger.exception(
            "process_ai_task unexpected",
            extra={"ai_event": "unexpected_error", "ai_task_id": task_id},
        )
        if credits_charged:
            QuotaManager.refund_credits(task, reason="unexpected_error")
        task.credits_used = 0
        task.status = AIProcessingTask.STATUS_FAILED
        task.error_message = str(exc)[:2000]
        task.completed_at = timezone.now()
        attach_failure_context(task, exc)
        task.save(
            update_fields=[
                "output_data",
                "status",
                "error_message",
                "completed_at",
                "credits_used",
                "updated_at",
            ]
        )
        return {"result": "error", "ai_task_id": task_id}


@shared_task
def check_pending_tasks() -> dict[str, int]:
    """
    Uzun süredir işlemde kalan ve webhook gelmemiş kayıtları yoklar.

    Returns:
        İstatistik sözlüğü (checked, updated).
    """
    cutoff = timezone.now() - timedelta(minutes=2)
    qs = (
        AIProcessingTask.all_objects.filter(
            status=AIProcessingTask.STATUS_PROCESSING,
            started_at__lt=cutoff,
            webhook_received_at__isnull=True,
        )
        .exclude(external_task_id="")[:200]
    )

    checked = 0
    updated = 0
    for task in qs.select_related("provider", "tenant"):
        checked += 1
        try:
            provider_impl = ProviderFactory.get_provider(task.provider.name)
        except AIProviderError:
            continue
        try:
            raw = run_provider_check_status(provider_impl, task.external_task_id)
        except AIProviderError:
            continue
        state = raw.lower()
        if state in {"completed", "succeeded", "done"}:
            task.status = AIProcessingTask.STATUS_COMPLETED
            task.completed_at = timezone.now()
            task.save(update_fields=["status", "completed_at", "updated_at"])
            updated += 1
        elif state in {"failed", "error", "cancelled", "canceled"}:
            QuotaManager.refund_credits(task, reason="poll_failed")
            task.credits_used = 0
            task.status = AIProcessingTask.STATUS_FAILED
            task.error_message = state
            task.completed_at = timezone.now()
            task.save(
                update_fields=[
                    "status",
                    "error_message",
                    "completed_at",
                    "credits_used",
                    "updated_at",
                ]
            )
            updated += 1
    logger.info(
        "check_pending_tasks tamamlandı",
        extra={
            "ai_event": "check_pending_tasks",
            "ai_checked": checked,
            "ai_updated": updated,
        },
    )
    return {"checked": checked, "updated": updated}


@shared_task
def reset_monthly_credits() -> int:
    """
    Tüm aboneliklerde harici AI kredi dönemini gerektiğinde sıfırlar.

    Returns:
        İşlenen abonelik sayısı (yaklaşık).
    """
    from apps.subscriptions.models import UserSubscription

    n = 0
    for sub in UserSubscription.objects.select_related("plan").iterator(chunk_size=500):
        if sub.plan is None or not sub.plan.external_ai_enabled:
            continue
        QuotaManager._ensure_ai_period(sub)
        n += 1
    return n


@shared_task
def cleanup_old_tasks() -> dict[str, int]:
    """
    90 günden eski terminal durumdaki görev kayıtlarını siler.

    Returns:
        ``{"deleted": n}`` — silinen görev satırı sayısı (silme öncesi sayım).
    """
    cutoff = timezone.now() - timedelta(days=90)
    terminal = (
        AIProcessingTask.STATUS_COMPLETED,
        AIProcessingTask.STATUS_FAILED,
        AIProcessingTask.STATUS_CANCELLED,
    )
    qs = AIProcessingTask.all_objects.filter(
        status__in=terminal,
        created_at__lt=cutoff,
    )
    n = qs.count()
    qs.delete()
    logger.info(
        "cleanup_old_tasks",
        extra={"ai_event": "cleanup_old_tasks", "ai_deleted": n},
    )
    return {"deleted": n}


@shared_task
def notify_task_completion(task_id: int) -> None:
    """
    Tamamlanan / başarısız görevler için bildirim kancası (log + ileride e-posta).

    Args:
        task_id: AIProcessingTask PK.
    """
    task = AIProcessingTask.all_objects.filter(pk=task_id).first()
    if task is None:
        return
    duration = task.processing_duration
    long_run = duration is not None and duration > timedelta(minutes=5)
    logger.info(
        "notify_task_completion",
        extra={
            "ai_event": "notify_task_completion",
            "ai_task_id": task_id,
            "ai_status": task.status,
            "ai_long_run": long_run,
        },
    )
    # E-posta / Channels entegrasyonu buraya bağlanabilir.
