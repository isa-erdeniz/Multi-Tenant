from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.urls import reverse

from apps.subscriptions.services import can_use_feature, get_remaining, increment_usage


class FeatureUsageMixin(LoginRequiredMixin):
    """Class-based view: feature_type ve kota kontrolü."""

    feature_type = None
    quota_exceeded_redirect = None
    consume_usage_on_dispatch = False

    def get_quota_redirect(self):
        return self.quota_exceeded_redirect or reverse("payments:upgrade")

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        ft = self.feature_type
        if ft and not can_use_feature(request.user, ft):
            messages.warning(
                request,
                "Bu özellik için plan limitiniz doldu veya deneme süreniz bitti.",
            )
            return redirect(self.get_quota_redirect())

        if ft and self.consume_usage_on_dispatch and request.method == "POST":
            increment_usage(request.user, ft)

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if self.feature_type:
            ctx["feature_remaining"] = get_remaining(
                self.request.user, self.feature_type
            )
        return ctx
