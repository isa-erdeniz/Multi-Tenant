"""
garment-core HTTP istemcisi — HMAC imzalı POST, retry, timeout.
Mehlr → garment-core (Node.js) yönünde veri gönderimini yönetir.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
import urllib.error
import urllib.request
from typing import Any

from django.conf import settings

logger = logging.getLogger("mehlr.integrations.garment_core")

_TIMEOUT = 10  # saniye
_MAX_RETRIES = 2


def _get_config() -> tuple[str, str]:
    url = getattr(settings, "GARMENT_CORE_WEBHOOK_URL", "").rstrip("/")
    secret = getattr(settings, "GARMENT_CORE_WEBHOOK_SECRET", "")
    return url, secret


def _sign(body: bytes, secret: str) -> str:
    """HMAC-SHA256 imzası — garment-core tarafında doğrulanır."""
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def send_to_garment_core(
    event: str,
    payload: dict[str, Any],
    *,
    tenant_slug: str = "mehlr",
) -> dict[str, Any] | None:
    """
    garment-core'a imzalı POST gönderir.
    Dönüş: yanıt dict veya None (bağlantı yok / devre dışı).
    """
    url, secret = _get_config()
    if not url:
        logger.debug("GARMENT_CORE_WEBHOOK_URL tanımlı değil; gönderim atlandı.")
        return None

    body = json.dumps(
        {"event": event, "tenant_slug": tenant_slug, "payload": payload},
        ensure_ascii=False,
    ).encode("utf-8")

    headers: dict[str, str] = {
        "Content-Type": "application/json; charset=utf-8",
        "X-Mehlr-Timestamp": str(int(time.time())),
    }
    if secret:
        headers["X-Hub-Signature-256"] = f"sha256={_sign(body, secret)}"

    last_err: Exception | None = None
    for attempt in range(_MAX_RETRIES + 1):
        try:
            req = urllib.request.Request(url, data=body, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
                raw = resp.read()
                result: dict[str, Any] = json.loads(raw) if raw else {}
                logger.info(
                    "garment_core ← event=%s tenant=%s status=%s",
                    event,
                    tenant_slug,
                    resp.status,
                )
                return result
        except urllib.error.HTTPError as exc:
            logger.warning(
                "garment_core HTTP %s event=%s attempt=%s", exc.code, event, attempt + 1
            )
            last_err = exc
            if exc.code < 500:
                break  # 4xx yeniden denemeden fayda yok
        except Exception as exc:
            logger.warning("garment_core bağlantı hatası event=%s attempt=%s: %s", event, attempt + 1, exc)
            last_err = exc
        if attempt < _MAX_RETRIES:
            time.sleep(2 ** attempt)

    logger.error("garment_core gönderimi başarısız event=%s: %s", event, last_err)
    return None
