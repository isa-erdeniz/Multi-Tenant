"""
garment-core → Mehlr bağlam kaynağı.
Garment-Core API'den (veya yerel DressifyeGarment) gardırop verisi çeker;
mevcut DressifyeClient ile aynı arayüzü döndürür.
"""
from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from typing import Any

from django.conf import settings

logger = logging.getLogger("mehlr.integrations.garment_core_context")

_TIMEOUT = 8


def _get_config() -> tuple[str, str]:
    url = getattr(settings, "GARMENT_CORE_API_URL", "").rstrip("/")
    key = getattr(settings, "GARMENT_CORE_API_KEY", "")
    return url, key


def fetch_garments_from_core(
    tenant_slug: str,
    limit: int = 50,
    cursor: str | None = None,
) -> list[dict[str, Any]]:
    """
    garment-core GET /v1/garments?tenant_slug=...&limit=...
    Dönüş: normalize edilmiş garment listesi (DressifyeGarment şemasına uyumlu).
    URL/anahtar yoksa boş liste döner — sistem mock'a düşer.
    """
    url, key = _get_config()
    if not url or not key:
        logger.debug("GARMENT_CORE_API_URL veya GARMENT_CORE_API_KEY eksik; atlandı.")
        return []

    params = f"tenant_slug={tenant_slug}&limit={limit}"
    if cursor:
        params += f"&cursor={cursor}"

    req = urllib.request.Request(
        f"{url}/v1/garments?{params}",
        headers={"Authorization": f"Bearer {key}"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            body: dict[str, Any] = json.loads(resp.read())
            items: list[dict[str, Any]] = body.get("items") or []
            return [_map_to_dressifye_shape(g) for g in items if isinstance(g, dict)]
    except urllib.error.HTTPError as exc:
        logger.warning("garment_core_context_source HTTP %s tenant=%s", exc.code, tenant_slug)
    except Exception as exc:
        logger.warning("garment_core_context_source hata tenant=%s: %s", tenant_slug, exc)
    return []


def _map_to_dressifye_shape(g: dict[str, Any]) -> dict[str, Any]:
    """
    garment-core satırını DressifyeClient / context_manager normalizer'ı ile uyumlu şekle çevirir.
    mehlr_attributes içindeki Mehlr 1.0 alanlarını metadata olarak taşır.
    """
    mehlr = g.get("mehlrAttributes") or g.get("mehlr_attributes") or {}
    if not isinstance(mehlr, dict):
        mehlr = {}

    payload = g.get("universalPayload") or g.get("universal_payload") or {}
    if not isinstance(payload, dict):
        payload = {}

    metadata: dict[str, Any] = {}
    for field in ("fabricType", "hairType", "styleEra", "cosmeticFinish", "colorPalette"):
        val = mehlr.get(field)
        if val is not None:
            metadata[field] = val
    metadata["source"] = payload.get("source_domain") or "garment_core"

    return {
        "id": g.get("externalRef") or g.get("external_ref") or g.get("id") or "",
        "name": g.get("title") or "",
        "category": g.get("normalizedCategory") or g.get("normalized_category") or "",
        "color": mehlr.get("colorPalette", [None])[0] if isinstance(mehlr.get("colorPalette"), list) else "",
        "size": "",
        "image_url": "",
        "metadata": metadata,
    }
