"""
Harici AI webhook URL'leri (CSRF muaf, imza doğrulamalı).
"""

from django.urls import path

from apps.ai_integrations import webhooks

urlpatterns = [
    path("wearview/", webhooks.wearview_webhook, name="webhook-wearview"),
    path("zmo/", webhooks.zmo_webhook, name="webhook-zmo"),
    path("style3d/", webhooks.style3d_webhook, name="webhook-style3d"),
]
