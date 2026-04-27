from django.shortcuts import redirect
from django.urls import reverse


class TrialMiddleware:
    """
    Trial süresi dolmuş kullanıcıları ödeme sayfasına yönlendirir.
    """
    EXEMPT_PATHS = [
        "/hesap/",
        "/odemeler/",
        "/odemeler/webhook/",
        "/abonelik/",
        "/admin/",
        "/static/",
        "/media/",
        "/health/",
        "/profil/onboarding/",
    ]

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if self._should_check(request):
            sub = getattr(request.user, "subscription", None)
            if sub and sub.is_trial_expired():
                return redirect(reverse("payments:upgrade"))

        return self.get_response(request)

    def _should_check(self, request):
        if not request.user.is_authenticated:
            return False
        path = request.path
        return not any(path.startswith(p) for p in self.EXEMPT_PATHS)
