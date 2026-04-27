"""
iyzico ödeme servisi.
SDK, base_url için tam URL değil yalnızca host (ve isteğe bağlı port) bekler;
ör. sandbox-api.iyzipay.com — ayarlar IYZICO_BASE_URL bunu normalize eder.
Sandbox API: https://sandbox-api.iyzipay.com
Production API: https://api.iyzipay.com
"""
import json
import logging
import uuid

from django.conf import settings

logger = logging.getLogger(__name__)


def _iyzico_credentials_configured() -> bool:
    api = (settings.IYZICO_API_KEY or "").strip()
    secret = (settings.IYZICO_SECRET_KEY or "").strip()
    return bool(api and secret)


def _log_iyzico_debug_config() -> None:
    """Tam anahtarları loglama; yalnızca DEBUG + host / api_key öneki / secret var mı."""
    if not settings.DEBUG:
        return
    key = (settings.IYZICO_API_KEY or "").strip()
    if key:
        prefix = f"{key[:10]}..." if len(key) > 10 else f"{key}..."
    else:
        prefix = "YOK"
    has_secret = bool((settings.IYZICO_SECRET_KEY or "").strip())
    logger.debug(
        "iyzico config: host=%s api_key_prefix=%s secret_configured=%s",
        settings.IYZICO_BASE_URL,
        prefix,
        has_secret,
    )


def _get_options():
    return {
        "api_key": settings.IYZICO_API_KEY,
        "secret_key": settings.IYZICO_SECRET_KEY,
        "base_url": settings.IYZICO_BASE_URL,
    }


def get_iyzico_plan_code(tier: str, interval: str) -> str:
    """
    Tier: STARTER, ELITE, PLATINUM, DIAMOND (büyük/küçük harf duyarsız).
    Interval: monthly / yearly veya MONTHLY / YEARLY.
    Diamond için yalnızca YEARLY kullanılır.
    Ayar adı: settings.IYZICO_PP_{TIER}_{INTERVAL} (örn. IYZICO_PP_ELITE_MONTHLY).
    """
    tier_u = (tier or "STARTER").strip().upper()
    interval_raw = (interval or "monthly").strip().upper()
    if interval_raw not in ("MONTHLY", "YEARLY"):
        interval_u = "MONTHLY"
    else:
        interval_u = interval_raw
    if tier_u == "DIAMOND":
        interval_u = "YEARLY"

    attr_name = f"IYZICO_PP_{tier_u}_{interval_u}"
    plan_code = (getattr(settings, attr_name, None) or "").strip()
    if plan_code:
        return plan_code

    # Eski tek referans env (ELITE / PLATINUM / DIAMOND); STARTER için yok
    legacy_map = {
        "ELITE": getattr(settings, "IYZICO_SUBSCRIPTION_PP_ELITE", "") or "",
        "PLATINUM": getattr(settings, "IYZICO_SUBSCRIPTION_PP_PLATINUM", "") or "",
        "DIAMOND": getattr(settings, "IYZICO_SUBSCRIPTION_PP_DIAMOND", "") or "",
    }
    legacy = (legacy_map.get(tier_u) or "").strip()
    if legacy:
        return legacy

    raise ValueError(
        f"Plan kodu bulunamadı: {attr_name} (ve eski IYZICO_SUBSCRIPTION_PP_* yedeği yok)"
    )


def create_checkout_form(user, plan, period: str, callback_url: str) -> dict:
    """
    iyzico CheckoutForm (tek seferlik ödeme).
    Otomatik yenileme için iyzico Subscription / Üyelik Ödemesi API ayrı entegre edilmelidir.
    """
    _log_iyzico_debug_config()
    if not _iyzico_credentials_configured():
        api_set = bool((settings.IYZICO_API_KEY or "").strip())
        secret_set = bool((settings.IYZICO_SECRET_KEY or "").strip())
        logger.error(
            "iyzico: ortamda API anahtarları eksik (IYZICO_API_KEY tanımlı=%s, "
            "IYZICO_SECRET_KEY tanımlı=%s). Railway Variables veya .env kontrol edin.",
            api_set,
            secret_set,
        )
        return {"success": False, "error": "iyzico API bilgileri bulunamadı"}

    try:
        import iyzipay
    except ImportError:
        logger.error("iyzipay paketi yüklenmemiş")
        return {"success": False, "error": "Ödeme sistemi yapılandırılmamış"}

    options = _get_options()

    amount = str(plan.price_yearly if period == "yearly" else plan.price_monthly)
    conversation_id = str(uuid.uuid4())

    profile = getattr(user, "profile", None)
    first_name = profile.first_name if profile and profile.first_name else "Kullanıcı"

    request_body = {
        "locale": "tr",
        "conversationId": conversation_id,
        "price": amount,
        "paidPrice": amount,
        "currency": getattr(settings, "IYZICO_CURRENCY", "TRY"),
        "basketId": f"dressifye_saas_{plan.slug}_{period}",
        "paymentGroup": "SUBSCRIPTION",
        "callbackUrl": callback_url,
        "enabledInstallments": ["1", "2", "3"],
        "buyer": {
            "id": str(user.id),
            "name": first_name,
            "surname": "",
            "gsmNumber": "+905000000000",
            "email": user.email,
            "identityNumber": "11111111111",
            "registrationAddress": "Türkiye",
            "ip": "85.34.78.112",
            "city": "Istanbul",
            "country": "Turkey",
        },
        "shippingAddress": {
            "contactName": first_name,
            "city": "Istanbul",
            "country": "Turkey",
            "address": "Türkiye",
        },
        "billingAddress": {
            "contactName": first_name,
            "city": "Istanbul",
            "country": "Turkey",
            "address": "Türkiye",
        },
        "basketItems": [
            {
                "id": plan.slug,
                "name": f"Dressifye {plan.name} — {period}",
                "category1": "Abonelik",
                "itemType": "VIRTUAL",
                "price": amount,
            }
        ],
    }

    try:
        checkout_form = iyzipay.CheckoutFormInitialize().create(
            request_body, options
        )
        result = checkout_form.read().decode("utf-8")
        data = json.loads(result)

        if data.get("status") == "success":
            return {
                "success": True,
                "token": data["token"],
                "form_content": data["checkoutFormContent"],
                "conversation_id": conversation_id,
            }
        else:
            logger.error(f"iyzico form hatası: {data.get('errorMessage')}")
            return {
                "success": False,
                "error": data.get("errorMessage", "Ödeme formu oluşturulamadı"),
            }

    except Exception as e:
        logger.exception(f"iyzico bağlantı hatası: {e}")
        return {"success": False, "error": str(e)}


def verify_payment(token: str) -> dict:
    """Callback'ten gelen token ile ödemeyi doğrula."""
    _log_iyzico_debug_config()
    if not _iyzico_credentials_configured():
        api_set = bool((settings.IYZICO_API_KEY or "").strip())
        secret_set = bool((settings.IYZICO_SECRET_KEY or "").strip())
        logger.error(
            "iyzico doğrulama: API anahtarları eksik (IYZICO_API_KEY tanımlı=%s, "
            "IYZICO_SECRET_KEY tanımlı=%s)",
            api_set,
            secret_set,
        )
        return {"success": False, "error": "iyzico API bilgileri bulunamadı"}

    try:
        import iyzipay
    except ImportError:
        return {"success": False, "error": "Ödeme sistemi yapılandırılmamış"}

    options = _get_options()

    request_body = {
        "locale": "tr",
        "conversationId": str(uuid.uuid4()),
        "token": token,
    }

    try:
        result = iyzipay.CheckoutForm().retrieve(request_body, options)
        data = json.loads(result.read().decode("utf-8"))

        if data.get("status") == "success" and data.get("paymentStatus") == "SUCCESS":
            return {
                "success": True,
                "payment_id": data.get("paymentId", ""),
                "amount": data.get("paidPrice", 0),
            }
        else:
            return {
                "success": False,
                "error": data.get("errorMessage", "Ödeme doğrulanamadı"),
            }

    except Exception as e:
        logger.exception(f"iyzico doğrulama hatası: {e}")
        return {"success": False, "error": str(e)}


def create_subscription_checkout_form(
    *,
    user,
    pricing_plan_reference_code: str,
    callback_url: str,
    conversation_id: str | None = None,
    subscription_initial_status: str = "ACTIVE",
) -> dict:
    """
    iyzico Subscription Checkout Form initialize (/v2/subscription/checkoutform/initialize).
    pricing_plan_reference_code: iyzico panelindeki Pricing Plan referans kodu.
    """
    _log_iyzico_debug_config()
    if not _iyzico_credentials_configured():
        return {"success": False, "error": "iyzico API bilgileri bulunamadı"}
    if not (pricing_plan_reference_code or "").strip():
        return {"success": False, "error": "pricing_plan_reference_code eksik"}

    try:
        import iyzipay
    except ImportError:
        logger.error("iyzipay paketi yüklenmemiş")
        return {"success": False, "error": "Ödeme sistemi yapılandırılmamış"}

    options = _get_options()
    conv = conversation_id or str(uuid.uuid4())
    profile = getattr(user, "profile", None)
    first = profile.first_name if profile and profile.first_name else "Kullanıcı"

    request_body = {
        "locale": "tr",
        "callbackUrl": callback_url,
        "pricingPlanReferenceCode": pricing_plan_reference_code.strip(),
        "subscriptionInitialStatus": subscription_initial_status,
        "conversationId": conv,
        "customer": {
            "name": first,
            "surname": "Dressifye",
            "email": user.email,
            "gsmNumber": "+905000000000",
            "identityNumber": "11111111111",
            "billingAddress": {
                "address": "Türkiye",
                "contactName": first,
                "city": "Istanbul",
                "country": "Turkey",
            },
            "shippingAddress": {
                "address": "Türkiye",
                "contactName": first,
                "city": "Istanbul",
                "country": "Turkey",
            },
        },
    }

    try:
        sub_form = iyzipay.SubscriptionCheckoutForm().create(request_body, options)
        data = json.loads(sub_form.read().decode("utf-8"))
        if data.get("status") == "success":
            return {
                "success": True,
                "token": data["token"],
                "form_content": data.get("checkoutFormContent", ""),
                "conversation_id": conv,
            }
        logger.error(
            "iyzico subscription form hatası: %s",
            data.get("errorMessage"),
        )
        return {
            "success": False,
            "error": data.get("errorMessage", "Abonelik formu oluşturulamadı"),
        }
    except Exception as e:
        logger.exception("iyzico subscription checkout bağlantı hatası: %s", e)
        return {"success": False, "error": str(e)}


def verify_subscription_checkout_form(token: str, conversation_id: str | None = None) -> dict:
    """
    Abonelik checkout tamamlandıktan sonra token ile sonucu çeker
    (GET /v2/subscription/checkoutform/{token}).
    Sunucu tarafında iyzico API + merchant secret ile doğrulanır.
    """
    _log_iyzico_debug_config()
    if not _iyzico_credentials_configured():
        return {"success": False, "error": "iyzico API bilgileri bulunamadı"}
    if not (token or "").strip():
        return {"success": False, "error": "token eksik"}

    try:
        import iyzipay
    except ImportError:
        return {"success": False, "error": "Ödeme sistemi yapılandırılmamış"}

    options = _get_options()
    request_body: dict = {"token": token.strip()}
    if conversation_id:
        request_body["conversationId"] = conversation_id

    try:
        raw = iyzipay.SubscriptionCheckoutForm().retrieve(request_body, options)
        data = json.loads(raw.read().decode("utf-8"))
        if data.get("status") != "success":
            return {
                "success": False,
                "error": data.get("errorMessage", "Abonelik sonucu alınamadı"),
            }
        inner = data.get("data") or {}
        sub_status = (inner.get("subscriptionStatus") or "").upper()
        if sub_status not in ("ACTIVE", "PENDING"):
            return {
                "success": False,
                "error": f"Abonelik durumu: {sub_status or 'bilinmiyor'}",
            }
        return {
            "success": True,
            "subscription_reference_code": inner.get("referenceCode", ""),
            "customer_reference_code": inner.get("customerReferenceCode", ""),
            "subscription_status": sub_status,
            "pricing_plan_reference_code": inner.get("pricingPlanReferenceCode", ""),
        }
    except Exception as e:
        logger.exception("iyzico subscription retrieve hatası: %s", e)
        return {"success": False, "error": str(e)}
