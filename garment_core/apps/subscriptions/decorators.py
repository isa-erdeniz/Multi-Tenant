from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse

from apps.subscriptions.services import can_use_feature, increment_usage


def require_feature_usage(feature_type, redirect_url=None, consume=False):
    """
    Özellik kullanımına izin var mı kontrol et.

    consume=True: yalnızca POST isteklerinde, view çalıştırılmadan *hemen önce*
    kullanımı artırır. View içinde doğrulama veya dosya kaydı varsa ve hata
    durumunda kota düşmemeli ise consume=False kullanıp, başarılı noktada
    apps.subscriptions.services.increment_usage çağırın (örn. tryon_start_view).

    GET ağırlıklı sayfalar (örn. editör) için kota tüketimi view içinde veya
    ayrı bir endpoint üzerinden yönetilir; bu decorator consume=True ile GET
    isteklerinde artış yapmaz.
    """

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect(reverse("account_login"))

            if not can_use_feature(request.user, feature_type):
                target = redirect_url or reverse("payments:upgrade")
                messages.warning(
                    request,
                    "Bu özellik için plan limitiniz doldu veya deneme süreniz bitti.",
                )
                return redirect(target)

            if consume and request.method == "POST":
                increment_usage(request.user, feature_type)

            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator
