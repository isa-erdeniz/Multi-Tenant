"""
Tenant bağlamı: contextvars + middleware ile TenantScopedManager uyumu.
"""
from __future__ import annotations

import contextvars
from contextlib import contextmanager
from typing import TYPE_CHECKING, Iterator

if TYPE_CHECKING:
    from apps.tenants.models import Tenant

_current_tenant: contextvars.ContextVar = contextvars.ContextVar(
    "dressifye_saas_current_tenant", default=None
)

_unscoped_depth: contextvars.ContextVar[int] = contextvars.ContextVar(
    "dressifye_saas_tenant_unscoped_depth", default=0
)


def get_current_tenant():
    """Aktif istek / with bloğu tenant'ı; yoksa None."""
    return _current_tenant.get()


def set_current_tenant(tenant) -> contextvars.Token:
    """Middleware tarafından kullanılır; token process_response'ta reset için."""
    return _current_tenant.set(tenant)


def reset_current_tenant(token: contextvars.Token | None) -> None:
    if token is not None:
        _current_tenant.reset(token)


def is_unscoped() -> bool:
    """True iken TenantScopedManager filtre uygulamaz (migrate, yönetim komutları)."""
    return _unscoped_depth.get() > 0


@contextmanager
def tenant_unscoped() -> Iterator[None]:
    """Migration / toplu iş: tüm tenant satırlarına erişim (dikkatli kullanın)."""
    t = _unscoped_depth.get()
    tok = _unscoped_depth.set(t + 1)
    try:
        yield
    finally:
        _unscoped_depth.reset(tok)


@contextmanager
def use_tenant(tenant: Tenant | None) -> Iterator[None]:
    """Celery / servis: geçici tenant bağlamı (tenant None ise sadece reset)."""
    if tenant is None:
        yield
        return
    tok = _current_tenant.set(tenant)
    try:
        yield
    finally:
        _current_tenant.reset(tok)
