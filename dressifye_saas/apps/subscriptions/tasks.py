import logging

from celery import shared_task
from django.utils import timezone

from apps.subscriptions.models import UserSubscription

logger = logging.getLogger(__name__)


@shared_task
def check_expired_subscriptions():
    """
    Bitiş tarihi geçmiş aktif/deneme abonelikleri 'expired' durumuna çeker.
    """
    now = timezone.now()
    qs = UserSubscription.objects.filter(
        status__in=["active", "trial"],
        end_date__isnull=False,
        end_date__lt=now,
    )
    n = qs.update(status="expired")
    if n:
        logger.info("check_expired_subscriptions: %s abonelik süresi doldu", n)
    return n


@shared_task
def reset_monthly_usage():
    """
    Geçmiş aylara ait FeatureUsage kayıtlarını temizler.
    """
    from apps.subscriptions.services import reset_monthly_usage_cleanup

    deleted = reset_monthly_usage_cleanup()
    if deleted:
        logger.info("reset_monthly_usage: %s eski kayıt silindi", deleted)
    return deleted
