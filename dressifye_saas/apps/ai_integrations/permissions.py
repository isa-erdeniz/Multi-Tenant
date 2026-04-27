"""DRF izinleri: kiracı bağlamı zorunluluğu."""

from __future__ import annotations

from django.utils.translation import gettext_lazy as _
from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView


class HasTenantContext(BasePermission):
    """İstekte çözümlenmiş `request.tenant` olmalıdır."""

    message = _("Tenant bağlamı gerekli.")

    def has_permission(self, request: Request, view: APIView) -> bool:
        tenant = getattr(request, "tenant", None)
        return tenant is not None and getattr(tenant, "is_active", False)
