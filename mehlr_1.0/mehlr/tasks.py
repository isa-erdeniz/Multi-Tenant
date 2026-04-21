"""
Celery görevleri — Dressifye gardırop senkronu, temizlik, toplu tarama.
"""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from celery import shared_task
from django.db import transaction
from django.utils import timezone

from mehlr.integrations.dressifye_client import DressifyeClient
from mehlr.models import DressifyeGarment, DressifyeUser, OutfitRecommendation, OutfitRecommendationFeedback
from mehlr.services.context_manager import bump_dressifye_context_cache_version

logger = logging.getLogger(__name__)


def _normalize_garment_row(raw: dict[str, Any], dressifye_user: DressifyeUser) -> tuple[str, dict[str, Any]]:
    ext = str(raw.get("id") or raw.get("external_id") or "").strip()
    if not ext:
        ext = str(raw.get("pk") or "")
    defaults = {
        "user": dressifye_user,
        "name": str(raw.get("name") or raw.get("title") or "")[:255],
        "category": str(raw.get("category") or raw.get("type") or "")[:100],
        "color": str(raw.get("color") or "")[:64],
        "size": str(raw.get("size") or "")[:32],
        "image_url": str(raw.get("image_url") or raw.get("image") or "")[:2048],
        "metadata": raw.get("metadata") if isinstance(raw.get("metadata"), dict) else {},
    }
    return ext, defaults


@shared_task(bind=True, max_retries=3, name="mehlr.tasks.sync_user_wardrobe")
def sync_user_wardrobe_task(self, user_id: str, force: bool = False) -> dict[str, Any]:
    """
    Dressifye API'den gardırop çekilir; DressifyeGarment kayıtları güncellenir.
    API'de olmayan yerel parçalar silinir.
    """
    _ = force  # İleride cache bypass / ek log için kullanılabilir
    client = DressifyeClient()
    try:
        items = client.get_user_wardrobe(user_id)
    except Exception as exc:
        logger.exception("sync_user_wardrobe: gardırop çekilemedi user_id=%s: %s", user_id, exc)
        raise self.retry(exc=exc, countdown=60) from exc

    dressifye_user, _ = DressifyeUser.objects.get_or_create(
        external_id=str(user_id),
        defaults={"username": f"user_{str(user_id)[:40]}"},
    )

    api_ids: set[str] = set()
    created = 0
    updated = 0

    with transaction.atomic():
        for raw in items:
            if not isinstance(raw, dict):
                continue
            ext, defaults = _normalize_garment_row(raw, dressifye_user)
            if not ext:
                continue
            api_ids.add(ext)
            obj, was_created = DressifyeGarment.objects.update_or_create(
                external_id=ext,
                defaults=defaults,
            )
            if was_created:
                created += 1
            else:
                updated += 1

        stale_qs = DressifyeGarment.objects.filter(user=dressifye_user).exclude(external_id__in=api_ids)
        removed = stale_qs.count()
        stale_qs.delete()

    bump_dressifye_context_cache_version(str(user_id))
    summary = {
        "user_id": user_id,
        "api_items": len(api_ids),
        "created": created,
        "updated": updated,
        "removed_local": removed,
    }
    logger.info("sync_user_wardrobe tamamlandı: %s", summary)
    return summary


@shared_task(name="mehlr.tasks.cleanup_old_data")
def cleanup_old_data(days: int = 30) -> dict[str, int]:
    """N günden eski kombin önerileri ve geri bildirimleri siler."""
    cutoff = timezone.now() - timedelta(days=days)
    with transaction.atomic():
        fb_del, _ = OutfitRecommendationFeedback.objects.filter(created_at__lt=cutoff).delete()
        rec_del, _ = OutfitRecommendation.objects.filter(created_at__lt=cutoff).delete()
    out = {"feedback_deleted": fb_del, "recommendations_deleted": rec_del}
    logger.info("cleanup_old_data: %s", out)
    return out


@shared_task(name="mehlr.tasks.batch_sync_all_active_users")
def batch_sync_all_active_users() -> dict[str, Any]:
    """Bilinen tüm Dressifye kullanıcıları için gardırop senkronunu kuyruğa atar."""
    ids = list(DressifyeUser.objects.values_list("external_id", flat=True))
    for uid in ids:
        sync_user_wardrobe_task.delay(str(uid), force=False)
    logger.info("batch_sync_all_active_users: %s kullanıcı kuyruğa alındı", len(ids))
    return {"queued": len(ids), "user_ids": [str(x) for x in ids]}
