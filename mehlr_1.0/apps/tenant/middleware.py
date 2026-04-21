"""
Tenant + hafif güvenlik katmanı.
Sıra: ErdenizSecurityMiddleware → TenantMiddleware → (diğerleri)
"""
from __future__ import annotations

import logging
import threading
from typing import TYPE_CHECKING, Any, Callable

from django.conf import settings
from django.core.cache import cache
from django.http import HttpRequest, HttpResponse

if TYPE_CHECKING:
    from apps.tenant.models import Tenant

logger = logging.getLogger("mehlr.tenant")

_thread_locals = threading.local()


def get_current_tenant() -> Tenant | None:
    """Şablon yükleyici ve AI katmanı için thread-local tenant."""
    return getattr(_thread_locals, "tenant", None)


def set_current_tenant(tenant: Tenant | None) -> None:
    _thread_locals.tenant = tenant


class ErdenizSecurityMiddleware:
    """
    Dış katman: basit oran sınırı + istek logu.
    Tam WAF / bot koruması için ``erdeniz_security`` paketi ayrıca yüklenebilir.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if getattr(settings, "DEBUG", False):
            return self.get_response(request)
        ip = request.META.get("REMOTE_ADDR", "unknown")
        key = f"tenant_sec:rl:{ip}"
        try:
            n = int(cache.get(key) or 0)
            if n > 2000:
                return HttpResponse("Too Many Requests", status=429)
            cache.set(key, n + 1, timeout=60)
        except Exception as e:
            logger.debug("Rate limit cache atlanıyor: %s", e)

        return self.get_response(request)


class TenantMiddleware:
    """HTTP_HOST ile tenant; thread-local + request.tenant."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        from apps.tenant.models import Tenant

        host = (request.get_host() or "").split(":")[0].lower().strip()
        tenant: Tenant | None = None
        if host:
            tenant = Tenant.objects.filter(domain=host, is_active=True).first()
        if not tenant:
            tenant = Tenant.objects.filter(slug="dressifye", is_active=True).first()

        request.tenant = tenant
        set_current_tenant(tenant)

        try:
            return self.get_response(request)
        finally:
            set_current_tenant(None)
