"""
Dressifye webhook işleyicileri — gardırop güncellemeleri, öğe silme, profil.
"""
from __future__ import annotations

import logging
from typing import Any

from django.db import transaction

from mehlr.models import DressifyeGarment, DressifyeUser
from mehlr.services.context_manager import invalidate_dressifye_context_cache

logger = logging.getLogger(__name__)


def invalidate_wardrobe_cache(user_id: str) -> None:
    """Tüm `dressifye_context:*` varyantlarını sürüm artırarak geçersiz kılar."""
    invalidate_dressifye_context_cache(user_id)


def process_dressifye_webhook(data: dict[str, Any]) -> bool:
    """
    Dressifye webhook gövdesini işler.

    Beklenen alanlar: ``event`` (veya ``type``), ``user_id``, ``external_id``, ``payload`` / ``data``.
    """
    event = (data.get("event") or data.get("type") or "").strip().lower()
    if not event:
        logger.warning("Dressifye webhook: event yok")
        return False

    if event == "wardrobe.updated":
        return _handle_wardrobe_updated(data)

    if event in ("item.deleted", "wardrobe.item_deleted"):
        return _handle_item_deleted(data)

    if event == "wardrobe.item_added":
        return _handle_wardrobe_item_added(data)

    if event == "user.profile_updated":
        return _handle_profile_updated(data)

    logger.info("Dressifye webhook: bilinmeyen event=%s", event)
    return True


def handle_dressifye_webhook(payload: dict[str, Any], event_type: str | None = None) -> bool:
    """``process_dressifye_webhook`` ile aynı; ``event_type`` verilirse payload'a eklenir."""
    merged = dict(payload)
    if event_type:
        merged.setdefault("event", event_type)
    return process_dressifye_webhook(merged)


def _user_id_from(data: dict[str, Any]) -> str | None:
    uid = data.get("user_id") or (data.get("data") or {}).get("user_id")
    if uid is None and isinstance(data.get("payload"), dict):
        uid = data["payload"].get("user_id")
    return str(uid).strip() if uid else None


def _external_id_from(data: dict[str, Any]) -> str | None:
    ext = (
        data.get("external_id")
        or data.get("garment_id")
        or (data.get("data") or {}).get("external_id")
    )
    if ext is None and isinstance(data.get("payload"), dict):
        ext = data["payload"].get("external_id")
    return str(ext).strip() if ext else None


def _handle_wardrobe_updated(data: dict[str, Any]) -> bool:
    user_id = _user_id_from(data)
    if not user_id:
        logger.warning("wardrobe.updated: user_id eksik")
        return False
    invalidate_wardrobe_cache(user_id)
    from mehlr.tasks import sync_user_wardrobe_task

    sync_user_wardrobe_task.delay(user_id, force=True)
    return True


def _handle_wardrobe_item_added(data: dict[str, Any]) -> bool:
    user_id = _user_id_from(data)
    if not user_id:
        return False
    invalidate_wardrobe_cache(user_id)
    from mehlr.tasks import sync_user_wardrobe_task

    sync_user_wardrobe_task.delay(user_id, force=True)
    return True


def _handle_item_deleted(data: dict[str, Any]) -> bool:
    ext = _external_id_from(data)
    if not ext:
        logger.warning("item.deleted: external_id eksik")
        return False
    with transaction.atomic():
        deleted, _ = DressifyeGarment.objects.filter(external_id=ext).delete()
        logger.info("DressifyeGarment silindi external_id=%s count=%s", ext, deleted)
    user_id = _user_id_from(data)
    if user_id:
        invalidate_wardrobe_cache(user_id)
    return True


def _handle_profile_updated(data: dict[str, Any]) -> bool:
    user_id = _user_id_from(data)
    if not user_id:
        return False
    profile = data.get("profile") or data.get("profile_data") or (data.get("data") or {}).get("profile")
    if isinstance(profile, dict):
        DressifyeUser.objects.filter(external_id=user_id).update(profile_data=profile)
    invalidate_wardrobe_cache(user_id)
    return True
