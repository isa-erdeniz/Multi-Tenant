from __future__ import annotations

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render


def tenant_landing(request: HttpRequest) -> HttpResponse:
    """Ana sayfa — tenant şablonu (yükleyici) veya kök ``landing.html``."""
    return render(request, "landing.html", {})
