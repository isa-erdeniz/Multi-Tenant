"""
erdeniz_security/middleware.py — SecurityHeaders, Audit, RequestSanitization.
"""
from __future__ import annotations

import logging
import re
import time
from typing import Callable

from django.http import HttpRequest, HttpResponse

logger = logging.getLogger(__name__)

SQL_PATTERNS = [r"(\s|^)(union|select|insert|update|delete|drop|exec)(\s|$)", r"'\s*or\s*'?\d+\s*=\s*'?\d+"]
XSS_PATTERNS = [r"<script[^>]*>", r"javascript:", r"on\w+\s*="]
PATH_TRAVERSAL = re.compile(r"\.\.[/\\]")


class SecurityHeadersMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)
        response["X-Content-Type-Options"] = "nosniff"
        response["X-Frame-Options"] = "DENY"
        response["X-XSS-Protection"] = "1; mode=block"
        response["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
        response["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline';"
        return response


class AuditMiddleware:
    SENSITIVE_PREFIXES = ("/admin/", "/api/auth/", "/api/token/", "/login/", "/logout/")

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        start = time.time()
        response = self.get_response(request)
        duration_ms = int((time.time() - start) * 1000)
        if any(request.path.startswith(p) for p in self.SENSITIVE_PREFIXES):
            try:
                from .audit import log_event
                user = getattr(request, "user", None)
                log_event(
                    "AUTH_SUCCESS" if (user and getattr(user, "pk", None)) else "AUTH_FAIL",
                    request.path[:255],
                    getattr(request, "_erdeniz_project", "unknown"),
                    user=user,
                    request=request,
                    success=response.status_code < 400,
                    duration_ms=duration_ms,
                )
            except Exception as e:
                logger.debug("Audit: %s", e)
        return response


class RequestSanitizationMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        raw = request.path + "?" + (request.META.get("QUERY_STRING") or "")
        raw_lower = raw.lower()
        for pat in SQL_PATTERNS + XSS_PATTERNS:
            if re.search(pat, raw_lower, re.IGNORECASE):
                logger.warning("Şüpheli pattern: %s", request.path)
                try:
                    from .audit import log_event
                    log_event("SECURITY_ALERT", request.path[:255], getattr(request, "_erdeniz_project", "unknown"), request=request, success=False, details={"reason": "suspicious_pattern"})
                except Exception:
                    pass
                return HttpResponse("Bad Request", status=400)
        if PATH_TRAVERSAL.search(raw):
            logger.warning("Path traversal: %s", request.path)
            return HttpResponse("Bad Request", status=400)
        return self.get_response(request)


class APIAuthenticationMiddleware:
    """API isteklerini doğrula: JWT → API key → Request signing → anonymous."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        request.auth_method = "anonymous"
        request.auth_project = None
        auth_header = request.META.get("HTTP_AUTHORIZATION") or ""
        if auth_header.startswith("Bearer "):
            request.auth_method = "jwt"
            return self.get_response(request)
        api_key = request.META.get("HTTP_X_API_KEY")
        if api_key:
            try:
                from .api_security import ErdenizAPIKeyManager
                mgr = ErdenizAPIKeyManager()
                info = mgr.validate_api_key(api_key)
                if info:
                    request.auth_method = "api_key"
                    request.auth_project = info.get("project")
            except Exception:
                pass
        if request.auth_method == "anonymous":
            try:
                from .api_security import RequestSigner
                from django.conf import settings
                secret = getattr(settings, "REQUEST_SIGNING_SECRET", None) or ""
                if secret and RequestSigner(secret).verify_request(request):
                    request.auth_method = "signed"
                    request.auth_project = request.META.get("HTTP_X_ERDENIZ_PROJECT") or "internal"
            except Exception:
                pass
        return self.get_response(request)


class APIRateLimitMiddleware:
    """ERDENIZ_RATE_LIMITS uygula; aşımda 429 + Retry-After + SECURITY_ALERT."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        try:
            from .api_security import ERDENIZ_RATE_LIMITS
            from django.core.cache import cache
            key = self._cache_key(request)
            limits = ERDENIZ_RATE_LIMITS.get("default", {})
            method = getattr(request, "auth_method", "anonymous")
            if method == "jwt" or (getattr(request, "user", None) and getattr(request.user, "pk", None)):
                rate = limits.get("user", "1000/hour")
            elif method == "api_key":
                rate = limits.get("api_key", "5000/hour")
            else:
                rate = limits.get("anon", "100/hour")
            num, period = self._parse_rate(rate)
            if not num or not key:
                return self.get_response(request)
            current = cache.get(key, 0)
            if current >= num:
                try:
                    from .audit import log_event
                    log_event("RATE_LIMIT_HIT", request.path[:255], getattr(request, "_erdeniz_project", "api"), request=request, success=False, details={"key": key})
                except Exception:
                    pass
                retry_after = 60 if "minute" in period else 3600
                resp = HttpResponse("Too Many Requests", status=429)
                resp["Retry-After"] = str(retry_after)
                return resp
            cache.set(key, current + 1, timeout=3600 if "hour" in period else 60)
        except Exception as e:
            logger.debug("Rate limit: %s", e)
        return self.get_response(request)

    def _cache_key(self, request: HttpRequest) -> str:
        method = getattr(request, "auth_method", "anon")
        uid = getattr(getattr(request, "user", None), "pk", None) or request.META.get("REMOTE_ADDR", "unknown")
        return f"erdeniz_rl:{method}:{uid}"

    def _parse_rate(self, rate: str) -> tuple[int, str]:
        try:
            n, p = rate.split("/")
            return int(n.strip()), p.strip().lower()
        except Exception:
            return 100, "hour"
