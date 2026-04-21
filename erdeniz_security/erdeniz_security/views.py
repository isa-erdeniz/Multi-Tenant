"""
erdeniz_security — Ekosistem servislerinden gelen güvenlik denetim isteklerini karşılar.
Özellikle packages/garment_core TS servisi bu endpoint'e POST yapar.
"""
import json
import logging

from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

logger = logging.getLogger(__name__)

ALLOWED_RESOURCE_TYPES = {
    "garment_ingest",
    "garment",
    "user_action",
    "api_request",
}


@method_decorator(csrf_exempt, name="dispatch")
class SecurityIngestView(View):
    """
    POST /erdeniz-security/ingest/

    Gelen payload:
      {
        "tenantId": "uuid",
        "tenantSlug": "stylecoree",
        "resourceType": "garment_ingest",
        "resourceId": "uuid | null",
        "payload": {...}
      }

    Dönen yanıt:
      { "verdict": "allowed" | "blocked" | "quarantined", "trace": {...} }

    Basit politika (genişletilebilir):
      - resourceType tanımlı değilse → quarantined
      - payload boşsa → quarantined
      - Diğer → allowed (gelecekte ML/kural tabanlı kontrol buraya eklenir)
    """

    http_method_names = ["post", "options"]

    def options(self, request, *args, **kwargs):
        return JsonResponse({}, status=204)

    def post(self, request, *args, **kwargs):
        try:
            body = json.loads(request.body.decode("utf-8")) if request.body else {}
        except (ValueError, json.JSONDecodeError):
            return JsonResponse(
                {"verdict": "blocked", "trace": {"reason": "invalid_json"}},
                status=400,
            )

        if not isinstance(body, dict):
            return JsonResponse(
                {"verdict": "blocked", "trace": {"reason": "body_not_object"}},
                status=400,
            )

        tenant_id = body.get("tenantId") or body.get("tenant_id", "")
        tenant_slug = body.get("tenantSlug") or body.get("tenant_slug", "")
        resource_type = body.get("resourceType") or body.get("resource_type", "")
        payload = body.get("payload", {})

        trace = {
            "tenant_id": tenant_id,
            "tenant_slug": tenant_slug,
            "resource_type": resource_type,
            "remote": True,
        }

        if resource_type not in ALLOWED_RESOURCE_TYPES:
            logger.warning(
                "SecurityIngest: bilinmeyen resourceType '%s' (tenant: %s)",
                resource_type,
                tenant_slug,
            )
            return JsonResponse(
                {
                    "verdict": "quarantined",
                    "trace": {**trace, "reason": "unknown_resource_type"},
                }
            )

        if not payload:
            return JsonResponse(
                {
                    "verdict": "quarantined",
                    "trace": {**trace, "reason": "empty_payload"},
                }
            )

        logger.info(
            "SecurityIngest allowed: tenant=%s resource_type=%s",
            tenant_slug,
            resource_type,
        )

        return JsonResponse(
            {"verdict": "allowed", "trace": {**trace, "reason": "policy_pass"}}
        )
