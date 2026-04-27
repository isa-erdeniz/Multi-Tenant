"""
İstek bağlamına tenant çözümler: özel domain veya header.
contextvars ile TenantScopedManager (wardrobe vb.) aynı tenant'ı görür.
"""
from __future__ import annotations

from apps.core.tenant_context import reset_current_tenant, set_current_tenant

try:
    from erdeniz_security.ecosystem_registry import slug_for_origin
except ImportError:
    def slug_for_origin(_origin: str) -> str | None:
        return None


HEADER_SLUG = "HTTP_X_GARMENT_CORE_TENANT_SLUG"
# İsteğe bağlı kısa alias
HEADER_SLUG_ALT = "HTTP_X_TENANT_SLUG"


class TenantContextMiddleware:
    """
    request.tenant: Tenant | None

    Çözüm sırası:
    1) X-Dressifye-Tenant-Slug veya X-Tenant-Slug
    2) Origin → ecosystem registry → slug → Tenant
    3) Host eşlemesi (Tenant.domain, www. öneki atılır)
    4) Giriş yapmış kullanıcının tenant'ı (geliştirme / ana domain)
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.tenant = None
        from apps.tenants.models import Tenant

        slug = request.META.get(HEADER_SLUG) or request.META.get(HEADER_SLUG_ALT)
        if slug:
            slug = str(slug).strip()
            if slug:
                request.tenant = Tenant.objects.filter(
                    slug__iexact=slug, is_active=True
                ).first()

        if request.tenant is None:
            origin = (request.META.get("HTTP_ORIGIN") or "").strip()
            if origin:
                oslug = slug_for_origin(origin)
                if oslug:
                    request.tenant = Tenant.objects.filter(
                        slug__iexact=oslug, is_active=True
                    ).first()

        if request.tenant is None:
            host = request.get_host().split(":")[0].lower()
            if host.startswith("www."):
                host = host[4:]
            if host:
                request.tenant = (
                    Tenant.objects.filter(
                        domain__iexact=host, is_active=True
                    )
                    .exclude(domain="")
                    .first()
                )

        if request.tenant is None and getattr(request, "user", None) is not None:
            if request.user.is_authenticated:
                ut = getattr(request.user, "tenant", None)
                if ut is not None and ut.is_active:
                    request.tenant = ut

        token = set_current_tenant(request.tenant)
        try:
            return self.get_response(request)
        finally:
            reset_current_tenant(token)
