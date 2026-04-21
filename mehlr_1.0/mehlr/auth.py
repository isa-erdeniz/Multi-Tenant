# mehlr/auth.py
import functools
from django.conf import settings
from django.contrib.auth import get_user_model
from django.http import JsonResponse

User = get_user_model()

def api_key_or_login_required(view_func):
    @functools.wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # Her request'te settings'ten oku (modül freeze sorunu yok)
        inter_service_key = getattr(settings, "INTER_SERVICE_API_KEY", "")
        api_key = request.headers.get("X-API-Key", "")

        if api_key and inter_service_key and api_key == inter_service_key:
            service_user, _ = User.objects.get_or_create(
                username="mehlr_service",
                defaults={"is_active": True, "email": "service@mehlr.internal"}
            )
            request.user = service_user
            request.is_service_request = True
            return view_func(request, *args, **kwargs)

        if not request.user.is_authenticated:
            if request.headers.get("HX-Request") or request.content_type == "application/json":
                return JsonResponse({"status": "error", "message": "Unauthorized"}, status=401)
            from django.contrib.auth.views import redirect_to_login
            return redirect_to_login(request.get_full_path())

        request.is_service_request = False
        return view_func(request, *args, **kwargs)
    return wrapper
