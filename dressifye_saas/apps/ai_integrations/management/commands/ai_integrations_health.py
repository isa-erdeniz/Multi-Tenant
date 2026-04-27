"""
Dahili sağlık kontrolü: aktif sağlayıcılar, Celery ping, kritik ortam anahtarları.
"""

from __future__ import annotations

import json
import sys
from typing import Any

from celery import current_app
from django.conf import settings
from django.core.management.base import BaseCommand

from apps.ai_integrations.models import AIProvider


class Command(BaseCommand):
    """Harici AI modülü için operasyonel özet (çıktı JSON)."""

    help = "AI sağlayıcıları, Celery worker görünürlüğü ve temel API ortam değişkenlerini kontrol eder."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument(
            "--strict",
            action="store_true",
            help="Aktif sağlayıcı yoksa veya Celery ping yanıt vermiyorsa çıkış kodu 1.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        active_providers = list(
            AIProvider.objects.filter(is_active=True).values_list("name", flat=True)
        )
        secrets_ok = {
            "WEARVIEW_API_KEY": bool(getattr(settings, "WEARVIEW_API_KEY", "")),
            "ZMO_API_KEY": bool(getattr(settings, "ZMO_API_KEY", "")),
            "STYLE3D_API_KEY": bool(getattr(settings, "STYLE3D_API_KEY", "")),
        }
        inspect = current_app.control.inspect(timeout=2.0)
        ping: dict[str, Any] | None = None
        try:
            ping = inspect.ping()
        except Exception as exc:  # noqa: BLE001
            ping = {"error": str(exc)}
        workers_alive = bool(ping) and all(isinstance(v, dict) for v in (ping or {}).values())
        report = {
            "active_providers": active_providers,
            "active_provider_count": len(active_providers),
            "secrets_configured": secrets_ok,
            "celery_ping": ping,
            "celery_workers_reachable": workers_alive,
        }
        self.stdout.write(json.dumps(report, indent=2, default=str))
        if options.get("strict") and (not active_providers or not workers_alive):
            sys.exit(1)
