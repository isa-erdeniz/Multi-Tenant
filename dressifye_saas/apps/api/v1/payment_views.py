"""Dressifye vitrin ↔ dressifye_saas ödeme / abonelik API."""
from __future__ import annotations

import logging
from decimal import Decimal

from django.conf import settings
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.payments.billing import apply_dressifye_subscription_entitlements
from apps.payments.iyzico_service import (
    create_subscription_checkout_form,
    get_iyzico_plan_code,
    verify_subscription_checkout_form,
)
from apps.payments.models import Payment
from apps.subscriptions.models import Plan

logger = logging.getLogger(__name__)

TIER_CHOICES = frozenset({"starter", "elite", "platinum", "diamond"})


def _plan_slug_for_tier(tier: str) -> str:
    m = {
        "starter": settings.DRESSIFYE_PLAN_SLUG_STARTER,
        "elite": settings.DRESSIFYE_PLAN_SLUG_ELITE,
        "platinum": settings.DRESSIFYE_PLAN_SLUG_PLATINUM,
        "diamond": settings.DRESSIFYE_PLAN_SLUG_DIAMOND,
    }
    return (m.get(tier) or settings.DRESSIFYE_PLAN_SLUG_ELITE).strip()


class DressifyeSubscriptionInitView(APIView):
    """JWT ile kimlik doğrulanmış kullanıcı için iyzico Subscription Checkout Form."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        tier = (request.data.get("tier") or "starter").lower().strip()
        if tier not in TIER_CHOICES:
            return Response(
                {
                    "error": (
                        "Geçersiz tier. starter, elite, platinum veya diamond gönderin."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        custom_title = (request.data.get("custom_title") or "").strip()[:120]
        # interval (önerilen) veya period (geriye dönük)
        interval_raw = request.data.get("interval") or request.data.get("period") or "monthly"
        period = str(interval_raw).lower().strip()
        if period not in ("monthly", "yearly"):
            period = "monthly"
        if tier == "diamond":
            period = "yearly"

        try:
            pp = get_iyzico_plan_code(tier, period)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        slug = _plan_slug_for_tier(tier)
        plan = Plan.objects.filter(slug=slug, is_active=True).first()
        if not plan:
            return Response(
                {"error": f"Plan bulunamadı veya pasif: {slug}"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        tenant = getattr(request.user, "tenant", None)
        if not tenant:
            return Response(
                {"error": "Hesap tenant kaydı eksik."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        callback_url = (settings.DRESSIFYE_SUBSCRIPTION_CALLBACK_URL or "").strip()
        if not callback_url:
            return Response(
                {"error": "DRESSIFYE_SUBSCRIPTION_CALLBACK_URL ayarlı değil."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        result = create_subscription_checkout_form(
            user=request.user,
            pricing_plan_reference_code=pp,
            callback_url=callback_url,
            subscription_initial_status="ACTIVE",
        )
        if not result["success"]:
            return Response(
                {"error": result.get("error", "Form oluşturulamadı")},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        Payment.objects.create(
            user=request.user,
            tenant=tenant,
            plan=plan,
            iyzico_token=result["token"],
            iyzico_conversation_id=result["conversation_id"],
            amount=Decimal("0"),
            period=period,
            status="pending",
            payment_kind="subscription_checkout",
            metadata={
                "dressifye_tier": tier,
                "dressifye_custom_title": custom_title,
                "source": "dressifye_pricing",
            },
        )

        return Response(
            {
                "checkout_form_content": result["form_content"],
                "token": result["token"],
                "conversation_id": result["conversation_id"],
            }
        )


class DressifyeSubscriptionCallbackView(APIView):
    """
    Dressifye Worker veya doğrudan istemci: iyzico token ile aboneliği doğrular.
    Doğrulama iyzico API retrieve ile sunucu tarafında yapılır (imza/secret SDK içinde).
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        token = (
            request.data.get("token")
            or request.POST.get("token")
            or request.query_params.get("token")
        )
        if not token:
            return Response({"error": "token gerekli"}, status=status.HTTP_400_BAD_REQUEST)

        payment = (
            Payment.objects.filter(
                iyzico_token=token,
                payment_kind="subscription_checkout",
                status="pending",
            )
            .select_related("user", "plan")
            .first()
        )
        if not payment:
            return Response(
                {"error": "Ödeme oturumu bulunamadı veya zaten işlendi"},
                status=status.HTTP_404_NOT_FOUND,
            )

        verified = verify_subscription_checkout_form(
            token,
            conversation_id=payment.iyzico_conversation_id,
        )
        if not verified["success"]:
            payment.status = "failed"
            payment.failure_reason = verified.get("error", "")[:2000]
            payment.save(update_fields=["status", "failure_reason", "updated_at"])
            return Response(
                {"error": verified.get("error", "Doğrulama başarısız")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        meta = payment.metadata or {}
        tier = (meta.get("dressifye_tier") or "elite").lower()
        custom_title = meta.get("dressifye_custom_title") or ""

        payment.status = "success"
        payment.iyzico_payment_id = (verified.get("subscription_reference_code") or "")[
            :200
        ]
        payment.save(update_fields=["status", "iyzico_payment_id", "updated_at"])

        apply_dressifye_subscription_entitlements(
            payment.user,
            plan=payment.plan,
            tier=tier,
            custom_title=custom_title,
            subscription_ref=verified.get("subscription_reference_code", ""),
            customer_ref=verified.get("customer_reference_code", ""),
            period=payment.period,
        )

        return Response({"ok": True})
