"""@audit_log, @require_api_key, @require_jwt, @require_signed_request, @rate_limit, @verify_webhook."""
from functools import wraps
from typing import Any, Callable

from .audit import log_event


def audit_log(resource_prefix: str = "", project: str = "erdeniz_security"):
    def decorator(view_func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(view_func)
        def _wrapped(request: Any, *args: Any, **kwargs: Any) -> Any:
            response = view_func(request, *args, **kwargs)
            try:
                log_event("CONFIG_CHANGE", (resource_prefix or request.path)[:255], project, request=request, success=getattr(response, "status_code", 200) < 400)
            except Exception:
                pass
            return response
        return _wrapped
    return decorator


def require_api_key(permissions: list[str] | None = None):
    """Sadece geçerli API key ve (opsiyonel) izinlerle erişim."""
    def decorator(view_func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(view_func)
        def _wrapped(request: Any, *args: Any, **kwargs: Any) -> Any:
            from django.http import HttpResponse
            key = request.META.get("HTTP_X_API_KEY") or (getattr(request, "headers", {}).get("X-Api-Key") if hasattr(request, "headers") else None)
            if not key:
                try:
                    log_event("API_AUTH_FAIL", request.path[:255], getattr(request, "_erdeniz_project", "api"), request=request, success=False, details={"reason": "missing_api_key"})
                except Exception:
                    pass
                return HttpResponse("API key required", status=401)
            from .api_security import ErdenizAPIKeyManager
            mgr = ErdenizAPIKeyManager()
            info = mgr.validate_api_key(key)
            if not info:
                return HttpResponse("Invalid API key", status=403)
            if permissions:
                key_perms = set(info.get("permissions") or [])
                if not key_perms.intersection(permissions) and "admin:all" not in key_perms:
                    try:
                        log_event("API_AUTH_FAIL", request.path[:255], getattr(request, "_erdeniz_project", "api"), request=request, success=False, details={"reason": "insufficient_permissions"})
                    except Exception:
                        pass
                    return HttpResponse("Insufficient permissions", status=403)
            request.auth_api_info = info
            return view_func(request, *args, **kwargs)
        return _wrapped
    return decorator


def require_jwt(view_func: Callable[..., Any]) -> Callable[..., Any]:
    """Sadece geçerli JWT ile erişim (DRF IsAuthenticated ile birlikte kullanılır)."""
    @wraps(view_func)
    def _wrapped(request: Any, *args: Any, **kwargs: Any) -> Any:
        from django.http import HttpResponse
        if not getattr(request, "user", None) or not getattr(request.user, "is_authenticated", lambda: False)():
            try:
                log_event("API_AUTH_FAIL", request.path[:255], getattr(request, "_erdeniz_project", "api"), request=request, success=False, details={"reason": "jwt_required"})
            except Exception:
                pass
            return HttpResponse("Authentication required", status=401)
        return view_func(request, *args, **kwargs)
    return _wrapped


def require_signed_request(view_func: Callable[..., Any]) -> Callable[..., Any]:
    """Sadece imzalı istekle erişim (projeler arası)."""
    @wraps(view_func)
    def _wrapped(request: Any, *args: Any, **kwargs: Any) -> Any:
        from django.http import HttpResponse
        from django.conf import settings
        from .api_security import RequestSigner
        secret = getattr(settings, "REQUEST_SIGNING_SECRET", None) or ""
        if not secret or not RequestSigner(secret).verify_request(request):
            try:
                log_event("API_AUTH_FAIL", request.path[:255], getattr(request, "_erdeniz_project", "api"), request=request, success=False, details={"reason": "invalid_signature"})
            except Exception:
                pass
            return HttpResponse("Invalid request signature", status=403)
        return view_func(request, *args, **kwargs)
    return _wrapped


def rate_limit(scope: str = "default"):
    """Hassas endpoint için rate limit (ERDENIZ_RATE_LIMITS[scope])."""
    def decorator(view_func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(view_func)
        def _wrapped(request: Any, *args: Any, **kwargs: Any) -> Any:
            from django.http import HttpResponse
            from django.core.cache import cache
            from .api_security import ERDENIZ_RATE_LIMITS
            limits = ERDENIZ_RATE_LIMITS.get(scope, ERDENIZ_RATE_LIMITS.get("default", {}))
            rate = list(limits.values())[0] if limits else "10/hour"
            try:
                n, p = rate.split("/")
                num = int(n.strip())
            except Exception:
                num = 10
            key = f"erdeniz_rl:{scope}:{request.META.get('REMOTE_ADDR', 'unknown')}"
            current = cache.get(key, 0)
            if current >= num:
                try:
                    log_event("RATE_LIMIT_HIT", request.path[:255], getattr(request, "_erdeniz_project", "api"), request=request, success=False, details={"scope": scope})
                except Exception:
                    pass
                r = HttpResponse("Too Many Requests", status=429)
                r["Retry-After"] = "60"
                return r
            cache.set(key, current + 1, timeout=3600)
            return view_func(request, *args, **kwargs)
        return _wrapped
    return decorator


def verify_webhook(category: str = "default"):
    """Webhook imza doğrulama (category=payment için verify_payment_webhook)."""
    def decorator(view_func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(view_func)
        def _wrapped(request: Any, *args: Any, **kwargs: Any) -> Any:
            from django.http import HttpResponse
            from .network_guard import WebhookVerifier
            verifier = WebhookVerifier()
            if category == "payment":
                provider = kwargs.get("provider") or request.GET.get("provider") or "iyzico"
                if not verifier.verify_payment_webhook(request, provider):
                    return HttpResponse("Webhook verification failed", status=403)
            else:
                import os
                secret = os.environ.get("WEBHOOK_SECRET", "") or ""
                try:
                    from decouple import config
                    secret = secret or config("WEBHOOK_SECRET", default="")
                except Exception:
                    pass
                if not secret or not verifier.verify_webhook(request, secret):
                    return HttpResponse("Webhook verification failed", status=403)
            return view_func(request, *args, **kwargs)
        return _wrapped
    return decorator


def secure_view(
    csp: str | None = None,
    frame_options: str = "DENY",
    hsts: bool = True,
    cache_control: str = "no-store, no-cache, must-revalidate",
):
    """View'a güvenlik HTTP başlıkları ekle."""
    def decorator(view_func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(view_func)
        def _wrapped(request: Any, *args: Any, **kwargs: Any) -> Any:
            response = view_func(request, *args, **kwargs)
            if not hasattr(response, "__setitem__"):
                return response
            response["X-Content-Type-Options"] = "nosniff"
            response["X-Frame-Options"] = frame_options
            response["X-XSS-Protection"] = "1; mode=block"
            response["Cache-Control"] = cache_control
            response["Pragma"] = "no-cache"
            if csp:
                response["Content-Security-Policy"] = csp
            if hsts:
                response["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
            return response
        return _wrapped
    return decorator


def permission_required_custom(
    permission: str,
    project: str | None = None,
    raise_exception: bool = True,
):
    """Granular yetki kontrolü. Django permission + ErdenizAPIKey izinleri."""
    def decorator(view_func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(view_func)
        def _wrapped(request: Any, *args: Any, **kwargs: Any) -> Any:
            from django.http import HttpResponseForbidden
            from django.shortcuts import redirect
            allowed = False
            if getattr(request, "user", None) and getattr(request.user, "is_authenticated", lambda: False)():
                if getattr(request.user, "has_perm", lambda p: False)(permission):
                    allowed = True
            if not allowed and getattr(request, "auth_api_info", None):
                perms = request.auth_api_info.get("permissions") or []
                if permission in perms or "admin:all" in perms:
                    allowed = True
            if not allowed:
                try:
                    log_event("AUTH_FAIL", request.path[:255], project or getattr(request, "_erdeniz_project", "api"), request=request, success=False, details={"permission": permission})
                except Exception:
                    pass
                if raise_exception:
                    return HttpResponseForbidden("Permission denied")
                return redirect("/login/")
            return view_func(request, *args, **kwargs)
        return _wrapped
    return decorator
