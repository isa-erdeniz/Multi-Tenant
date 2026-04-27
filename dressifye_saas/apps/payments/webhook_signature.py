"""
iyzico webhook X-Iyz-Signature-V3 doğrulaması.

Dokümantasyon: https://docs.iyzico.com/en/advanced/webhook (Direct / HPP / Subscription formatları)
"""
from __future__ import annotations

import hashlib
import hmac
import logging
from typing import Any

from django.conf import settings

logger = logging.getLogger(__name__)


def _hmac_sha256_hex(secret_key: str, message: str) -> str:
    return hmac.new(
        secret_key.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def _event_type(payload: dict[str, Any]) -> str:
    return str(
        payload.get("iyziEventType")
        or payload.get("eventType")
        or payload.get("event_type")
        or ""
    )


def _signature_candidates(payload: dict[str, Any], secret_key: str, merchant_id: str) -> list[str]:
    """Olası imza değerleri (payload biçimine göre)."""
    et = _event_type(payload)
    sk = str(secret_key)
    out: list[str] = []

    # --- Direct: secretKey + iyziEventType + paymentId + paymentConversationId + status
    pay_id = payload.get("paymentId")
    pconv = payload.get("paymentConversationId")
    st = str(payload.get("status") or "")
    if pay_id is not None and pconv is not None:
        msg = sk + et + str(pay_id) + str(pconv) + st
        out.append(_hmac_sha256_hex(sk, msg))

    # --- HPP (Checkout Form): secretKey + iyziEventType + iyziPaymentId + token + paymentConversationId + status
    iyzi_pid = payload.get("iyziPaymentId")
    tok = payload.get("token")
    pconv2 = payload.get("paymentConversationId")
    if iyzi_pid is not None and tok is not None and pconv2 is not None:
        msg = sk + et + str(iyzi_pid) + str(tok) + str(pconv2) + st
        out.append(_hmac_sha256_hex(sk, msg))

    # --- Subscription: merchantId + secretKey + eventType + subscriptionReferenceCode + orderReferenceCode + customerReferenceCode
    sub_ref = payload.get("subscriptionReferenceCode")
    order_ref = payload.get("orderReferenceCode")
    cust_ref = payload.get("customerReferenceCode")
    mid = str(merchant_id or payload.get("merchantId") or "")
    if sub_ref is not None and order_ref is not None and cust_ref is not None:
        msg = mid + sk + et + str(sub_ref) + str(order_ref) + str(cust_ref)
        out.append(_hmac_sha256_hex(sk, msg))

    return out


def verify_iyzico_webhook_signature(request, payload: dict[str, Any]) -> bool:
    """
    X-Iyz-Signature-V3 başlığını doğrula.

    IYZICO_WEBHOOK_VERIFY_SIGNATURE=False ise her zaman True (geliştirme).
    İmza yoksa ve IYZICO_WEBHOOK_ALLOW_UNSIGNED=True ise True (sandbox / eski entegrasyon).
    """
    if not getattr(settings, "IYZICO_WEBHOOK_VERIFY_SIGNATURE", True):
        return True

    secret_key = (getattr(settings, "IYZICO_SECRET_KEY", None) or "").strip()
    if not secret_key:
        logger.error("iyzico webhook: IYZICO_SECRET_KEY tanımlı değil; imza doğrulanamıyor")
        return False

    received = (request.headers.get("X-Iyz-Signature-V3") or "").strip()
    if not received:
        if getattr(settings, "IYZICO_WEBHOOK_ALLOW_UNSIGNED", False):
            logger.warning(
                "iyzico webhook: X-Iyz-Signature-V3 yok; ALLOW_UNSIGNED nedeniyle kabul edildi"
            )
            return True
        logger.warning("iyzico webhook: X-Iyz-Signature-V3 eksik")
        return False

    merchant_id = (getattr(settings, "IYZICO_MERCHANT_ID", None) or "").strip()
    candidates = _signature_candidates(payload, secret_key, merchant_id)
    if not candidates:
        logger.warning(
            "iyzico webhook: imza için uygun alan yok (keys=%s)",
            list(payload.keys())[:20],
        )
        if getattr(settings, "IYZICO_WEBHOOK_ALLOW_UNSIGNED", False):
            return True
        return False

    received_lower = received.lower()
    for c in candidates:
        if hmac.compare_digest(c.lower(), received_lower):
            return True

    logger.warning("iyzico webhook: imza eşleşmedi")
    return False
