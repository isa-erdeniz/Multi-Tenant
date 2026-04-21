import logging

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import ListView, TemplateView

from apps.subscriptions.models import Plan, UserSubscription

logger = logging.getLogger(__name__)


class PlanListView(ListView):
    """Aktif ücretli planlar (ödeme akışı payments uygulamasında)."""

    model = Plan
    template_name = "subscriptions/plan_list.html"
    context_object_name = "plans"

    def get_queryset(self):
        return Plan.objects.filter(is_active=True).order_by("order", "pk")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if self.request.user.is_authenticated:
            ctx["current_sub"] = getattr(
                self.request.user, "subscription", None
            )
        else:
            ctx["current_sub"] = None
        return ctx


class SubscriptionCheckoutView(LoginRequiredMixin, View):
    """Plan seçiminden sonra mevcut iyzico ödeme akışına yönlendir."""

    def get(self, request, plan_slug):
        period = request.GET.get("period", "monthly")
        base = reverse("payments:checkout", kwargs={"plan_slug": plan_slug})
        return redirect(f"{base}?period={period}")


class SubscriptionSuccessView(LoginRequiredMixin, View):
    """Ödeme başarı URL'si payments:success ile aynı sayfaya gider."""

    def get(self, request):
        return redirect("payments:success")


class SubscriptionCancelView(LoginRequiredMixin, View):
    """Aboneliği iptal (veritabanı); iyzico abonelik API ayrı entegrasyon gerektirir."""

    def post(self, request):
        sub = getattr(request.user, "subscription", None)
        if not sub:
            messages.error(request, "Kayıtlı abonelik bulunamadı.")
            return redirect("subscriptions:detail")

        sub.status = "cancelled"
        sub.end_date = timezone.now()
        sub.save()
        messages.info(request, "Aboneliğiniz iptal olarak işaretlendi.")
        logger.info("Abonelik iptal: %s", request.user.email)
        return redirect("subscriptions:detail")


class SubscriptionDetailView(LoginRequiredMixin, TemplateView):
    template_name = "subscriptions/subscription_detail.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        sub, _ = UserSubscription.objects.get_or_create(
            user=self.request.user,
            defaults={"tenant_id": self.request.user.tenant_id},
        )
        ctx["subscription"] = sub
        return ctx
