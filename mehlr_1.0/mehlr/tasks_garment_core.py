"""
Celery görevleri — Mehlr → garment-core köprüsü.
Django request döngüsünü bloklamaz; arka planda gönderim yapar.
"""
from __future__ import annotations

import logging
from typing import Any

from celery import shared_task

from mehlr.integrations.garment_core_client import send_to_garment_core

logger = logging.getLogger("mehlr.tasks_garment_core")


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    name="mehlr.tasks.push_garment_to_core",
)
def push_garment_to_core(
    self,
    garment_external_id: str,
    garment_data: dict[str, Any],
    tenant_slug: str = "dressifye",
) -> dict[str, Any]:
    """
    Tek bir DressifyeGarment kaydını garment-core'a ingest eder.
    Celery retry mekanizması ile geçici hatalara karşı dayanıklıdır.
    """
    try:
        result = send_to_garment_core(
            event="garment.upserted",
            payload={
                "external_ref": garment_external_id,
                "raw": garment_data,
            },
            tenant_slug=tenant_slug,
        )
        logger.info("push_garment_to_core: gönderildi external_id=%s", garment_external_id)
        return {"sent": True, "result": result}
    except Exception as exc:
        logger.warning(
            "push_garment_to_core başarısız external_id=%s: %s", garment_external_id, exc
        )
        raise self.retry(exc=exc) from exc


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    name="mehlr.tasks.push_outfit_recommendation_to_core",
)
def push_outfit_recommendation_to_core(
    self,
    recommendation_id: int,
    tenant_slug: str = "dressifye",
) -> dict[str, Any]:
    """
    OutfitRecommendation garment-core'a bildirilir; `synced_to_dressifye` işaretlenir.
    """
    from mehlr.models import OutfitRecommendation

    try:
        rec = OutfitRecommendation.objects.select_related("user").prefetch_related("garments").get(pk=recommendation_id)
    except OutfitRecommendation.DoesNotExist:
        logger.warning("push_outfit_recommendation_to_core: pk=%s bulunamadı", recommendation_id)
        return {"sent": False, "reason": "not_found"}

    payload = {
        "recommendation_id": rec.pk,
        "user_external_id": rec.user.external_id,
        "occasion": rec.occasion,
        "style_notes": rec.style_notes,
        "color_palette": rec.color_palette,
        "garment_ids": list(rec.garments.values_list("external_id", flat=True)),
    }

    try:
        result = send_to_garment_core(
            event="recommendation.created",
            payload=payload,
            tenant_slug=tenant_slug,
        )
        OutfitRecommendation.objects.filter(pk=recommendation_id).update(synced_to_dressifye=True)
        logger.info("push_outfit_recommendation_to_core: pk=%s gönderildi", recommendation_id)
        return {"sent": True, "result": result}
    except Exception as exc:
        raise self.retry(exc=exc) from exc
