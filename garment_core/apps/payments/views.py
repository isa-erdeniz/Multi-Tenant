import logging

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse

from apps.subscriptions.models import Plan, UserSubscription

from .billing import activate_subscription
from .models import Payment
from .iyzico_service import create_checkout_form, verify_payment

logger = logging.getLogger(__name__)


@login_required
def upgrade_view(request):
    """Plan seçim ve ödeme başlatma sayfası"""
    plans = Plan.objects.filter(is_active=True).exclude(slug="ucretsiz")
    sub = getattr(request.user, "subscription", None)
    days_left = sub.trial_days_left() if sub else 0

    return render(
        request,
        "payments/upgrade.html",
        {
            "plans": plans,
            "sub": sub,
            "days_left": days_left,
        },
    )


@login_required
def checkout_view(request, plan_slug):
    """iyzico ödeme formu"""
    plan = get_object_or_404(Plan, slug=plan_slug, is_active=True)
    period = request.GET.get("period", "monthly")

    if plan.slug == "ucretsiz":
        messages.info(request, "Ücretsiz plan zaten aktiftir.")
        return redirect("payments:upgrade")

    tenant = getattr(request.user, "tenant", None)
    if not tenant:
        messages.error(
            request,
            "Hesap tenant kaydı eksik. Lütfen destek ile iletişime geçin.",
        )
        return redirect("payments:upgrade")

    callback_url = request.build_absolute_uri(reverse("payments:callback"))

    result = create_checkout_form(
        user=request.user,
        plan=plan,
        period=period,
        callback_url=callback_url,
    )

    if not result["success"]:
        messages.error(
            request, f"Ödeme formu oluşturulamadı: {result.get('error', 'Hata')}"
        )
        return redirect("payments:upgrade")

    request.session["iyzico_token"] = result["token"]
    request.session["iyzico_plan_slug"] = plan_slug
    request.session["iyzico_period"] = period
    request.session["iyzico_conv_id"] = result["conversation_id"]

    amount = plan.price_yearly if period == "yearly" else plan.price_monthly
    Payment.objects.create(
        user=request.user,
        tenant=tenant,
        plan=plan,
        iyzico_token=result["token"],
        iyzico_conversation_id=result["conversation_id"],
        amount=amount,
        period=period,
        status="pending",
    )

    return render(
        request,
        "payments/checkout.html",
        {
            "plan": plan,
            "period": period,
            "amount": amount,
            "form_content": result["form_content"],
        },
    )


@login_required
def callback_view(request):
    """iyzico ödeme sonucu — POST callback"""
    token = request.POST.get("token") or request.GET.get("token")

    if not token:
        messages.error(request, "Geçersiz ödeme oturumu.")
        return redirect("payments:upgrade")

    result = verify_payment(token)

    payment = Payment.objects.filter(iyzico_token=token).first()

    if not payment or payment.user_id != request.user.id:
        messages.error(request, "Bu ödeme oturumu hesabınıza ait değil.")
        return redirect("payments:upgrade")

    if (
        payment.tenant_id
        and request.user.tenant_id
        and payment.tenant_id != request.user.tenant_id
    ):
        messages.error(
            request,
            "Ödeme kaydı bağlı olduğunuz organizasyon ile eşleşmiyor.",
        )
        return redirect("payments:upgrade")

    if result["success"]:
        if payment:
            payment.status = "success"
            payment.iyzico_payment_id = result.get("payment_id", "")
            payment.save(update_fields=["status", "iyzico_payment_id"])

        activate_subscription(
            user=request.user,
            plan=payment.plan if payment else None,
            period=payment.period if payment else "monthly",
        )

        messages.success(request, "🎉 Ödeme başarılı! Aboneliğiniz aktif edildi.")
        return redirect("payments:success")

    else:
        if payment:
            payment.status = "failed"
            payment.failure_reason = result.get("error", "")
            payment.save(update_fields=["status", "failure_reason"])

        messages.error(
            request,
            f"Ödeme başarısız: {result.get('error', 'Bilinmeyen hata')}",
        )
        return redirect("payments:upgrade")


@login_required
def success_view(request):
    return render(
        request,
        "payments/success.html",
        {"subscription": getattr(request.user, "subscription", None)},
    )
