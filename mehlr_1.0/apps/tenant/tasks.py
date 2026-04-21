"""
Celery — kaynak tenant verisini merkez (dressifye / master) ile senkronize eder.
"""
from __future__ import annotations

import logging
from typing import Any

from celery import shared_task
from django.db import transaction

from apps.tenant.models import CrossTenantData, Tenant

logger = logging.getLogger(__name__)


def collect_user_data_from_source(source: Tenant, user_external_id: str) -> dict[str, Any]:
    """
    Kaynak domaindeki kullanıcı verisini toplar.
    Üretimde: hairinfinity / stylecoree / styleforhuman API veya yerel modeller.
    """
    # Stub: gerçek entegrasyonda domain API çağrıları burada.
    return {
        "source_slug": source.slug,
        "data_type": source.data_type,
        "user_external_id": str(user_external_id),
    }


def push_to_target_tenant(
    target: Tenant,
    user_external_id: str,
    data_type: str,
    user_data: dict[str, Any],
) -> None:
    """Merkez tenant’ta DressifyeUser.profile_data içine birleşik profil yazar."""
    if target.data_type != Tenant.DataType.MASTER:
        return

    from mehlr.models import DressifyeUser
    from mehlr.services.context_manager import PROFILE_KEY_HAIR_INFINITY, invalidate_dressifye_context_cache

    with transaction.atomic():
        user, _ = DressifyeUser.objects.select_for_update().get_or_create(
            external_id=str(user_external_id),
            defaults={"username": f"user_{str(user_external_id)[:40]}"},
        )
        profile = user.profile_data if isinstance(user.profile_data, dict) else {}
        sources = profile.setdefault("cross_tenant_sources", {})
        sources[data_type] = user_data
        if data_type == Tenant.DataType.HAIR:
            hi = profile.setdefault(PROFILE_KEY_HAIR_INFINITY, {})
            if isinstance(hi, dict):
                hi.update(user_data)
            else:
                profile[PROFILE_KEY_HAIR_INFINITY] = dict(user_data)
        user.profile_data = profile
        user.save(update_fields=["profile_data", "updated_at"])
    if data_type == Tenant.DataType.HAIR:
        invalidate_dressifye_context_cache(user_external_id)


@shared_task(name="apps.tenant.tasks.sync_data_to_master")
def sync_data_to_master(source_tenant_slug: str, user_id: str) -> dict[str, Any]:
    """
    Örn. hairinfinitye.com’dan toplanan veriyi dressifye (master) tenant’a işler
    ve CrossTenantData kaydı oluşturur.
    """
    try:
        source = Tenant.objects.select_related("sync_to_tenant").get(
            slug=source_tenant_slug,
            is_active=True,
        )
    except Tenant.DoesNotExist:
        logger.warning("sync_data_to_master: tenant yok slug=%s", source_tenant_slug)
        return {"ok": False, "reason": "tenant_not_found", "slug": source_tenant_slug}

    target = source.sync_to_tenant
    if not target:
        return {"ok": False, "reason": "sync_to_tenant yok", "slug": source_tenant_slug}

    user_data = collect_user_data_from_source(source, user_id)

    push_to_target_tenant(target, user_id, source.data_type, user_data)

    row = CrossTenantData.objects.create(
        source_tenant=source,
        target_tenant=target,
        user_external_id=str(user_id),
        data_type=source.data_type,
        data_payload=user_data,
    )

    return {
        "ok": True,
        "cross_tenant_data_id": row.pk,
        "source": source.slug,
        "target": target.slug,
    }
