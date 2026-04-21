from __future__ import annotations

from typing import Any

from django.http import HttpRequest


def tenant_context(request: HttpRequest) -> dict[str, Any]:
    t = getattr(request, "tenant", None)
    slug = t.slug if t else "dressifye"
    return {
        "tenant": t,
        "tenant_slug": slug,
    }
