"""
iyzico webhook — abonelik / yenileme bildirimleri.

X-Iyz-Signature-V3: webhook_signature. Idempotency: WebhookEvent + webhook_idempotency_key
(iyziReferenceCode veya gövde özeti); tekrarlayan istekler 200 + idempotent.
"""
import json
import logging

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from apps.subscriptions.models import UserSubscription

from .billing import extend_subscription_renewal
from .iyzico_service import verify_payment
from .models import Payment, WebhookEvent, webhook_idempotency_key
from .webhook_signature import verify_iyzico_webhook_signature

logger = logging.getLogger(__name__)


def _handle_subscription_order(payload: dict) -> None:
    """
    SUBSCRIPTION_ORDER: token ile ödeme doğrula, Payment güncelle, aboneliği uzat.
    """
    token = (
        payload.get("token")
        or payload.get("paymentToken")
        or payload.get("iyziPaymentToken")
    )
    if not token:
        logger.warning("SUBSCRIPTION_ORDER: token yok, payload keys=%s", list(payload.keys()))
        return

    result = verify_payment(token)
    if not result.get("success"):
        logger.error(
            "SUBSCRIPTION_ORDER: doğrulama başarısız: %s",
            result.get("error", "?"),
        )
        return

    payment = Payment.objects.filter(iyzico_token=token).first()
    if not payment:
        conv = (
            payload.get("conversationId")
            or payload.get("paymentConversationId")
            or payload.get("conversation_id")
        )
        if conv:
            payment = (
                Payment.objects.filter(iyzico_conversation_id=str(conv))
                .order_by("-created_at")
                .first()
            )
    if not payment:
        logger.warning(
            "SUBSCRIPTION_ORDER: Payment bulunamadı (token=%s...)",
            token[:12] if token else "",
        )
        return

    u = payment.user
    if (
        payment.tenant_id
        and getattr(u, "tenant_id", None)
        and payment.tenant_id != u.tenant_id
    ):
        logger.error(
            "SUBSCRIPTION_ORDER: Payment %s tenant ile kullanıcı tenant uyuşmuyor",
            payment.pk,
        )
        return

    payment.status = "success"
    payment.iyzico_payment_id = result.get("payment_id") or payment.iyzico_payment_id
    payment.save()

    if not payment.plan_id:
        logger.warning("SUBSCRIPTION_ORDER: payment %s plan yok", payment.pk)
        return

    extend_subscription_renewal(
        payment.user,
        payment.plan,
        payment.period,
    )


def _dispatch_webhook(payload: dict) -> None:
    event_type = payload.get("iyziEventType") or payload.get("eventType")
    if event_type == "SUBSCRIPTION_ORDER":
        _handle_subscription_order(payload)
    elif event_type == "SUBSCRIPTION_CANCELED":
        ref = payload.get("subscriptionReferenceCode")
        if ref:
            UserSubscription.objects.filter(iyzico_subscription_ref=ref).update(
                status="cancelled"
            )
    elif event_type == "BASKET_ITEM_ON_SUBSCRIPTION_RENEWAL_PAYMENT":
        _handle_subscription_order(payload)


@csrf_exempt
@require_POST
def iyzico_webhook(request):
    raw_body = request.body
    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError:
        return JsonResponse(
            {"status": "error", "message": "Invalid JSON"}, status=400
        )

    if not verify_iyzico_webhook_signature(request, payload):
        return JsonResponse(
            {"status": "error", "message": "Invalid signature"},
            status=403,
        )

    event_type = payload.get("iyziEventType") or payload.get("eventType")
    logger.info("iyzico webhook received: %s", event_type)

    idem_key = webhook_idempotency_key(payload, raw_body)
    _, created = WebhookEvent.objects.get_or_create(
        reference_code=idem_key,
        defaults={"event_type": event_type or ""},
    )
    if not created:
        logger.info("iyzico webhook idempotent skip: %s", idem_key[:24])
        return JsonResponse({"status": "ok", "idempotent": True})

    try:
        _dispatch_webhook(payload)
    except Exception:
        logger.exception("iyzico webhook işlenirken hata")
        WebhookEvent.objects.filter(reference_code=idem_key).delete()
        raise

    return JsonResponse({"status": "ok"})
