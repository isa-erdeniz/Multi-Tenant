import json
import secrets

from django.conf import settings
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from apps.intake.models import IntakeRecord

try:
    from erdeniz_security.ecosystem_registry import origins_for_slug, slug_for_origin
except ImportError:
    def slug_for_origin(_origin: str) -> str | None:
        return None

    def origins_for_slug(_slug: str) -> list:
        return []


def _bearer(request) -> str:
    h = request.META.get("HTTP_AUTHORIZATION", "")
    if h.startswith("Bearer "):
        return h[7:].strip()
    return ""


def _resolve_tenant_slug(request) -> str | None:
    raw = (
        request.META.get("HTTP_X_TENANT_ID", "")
        or request.META.get("HTTP_X_TENANT_SLUG", "")
        or ""
    ).strip()
    if raw:
        return raw
    try:
        body = json.loads(request.body.decode("utf-8")) if request.body else {}
    except (ValueError, json.JSONDecodeError):
        body = {}
    ts = body.get("tenant_slug") or body.get("tenant") or body.get("project")
    if isinstance(ts, str) and ts.strip():
        return ts.strip()
    return None


@method_decorator(csrf_exempt, name="dispatch")
class MultiSourceIntakeView(View):
    """
    POST /api/v1/intake/

    Tenant:
      - X-Tenant-ID veya X-Tenant-Slug (HTTP_X_TENANT_ID / HTTP_X_TENANT_SLUG)
      - veya JSON: tenant_slug | tenant | project

    Kaynak doğrulama (Origin varsa):
      - ecosystem registry'de bu tenant için tanımlı kökenlerden biri olmalı
    """

    http_method_names = ["post", "options"]

    def options(self, request):
        return JsonResponse({}, status=204)

    def post(self, request):
        expected = getattr(settings, "INTAKE_BEARER_TOKEN", "") or ""
        if not expected:
            return JsonResponse(
                {"error": "intake_not_configured"},
                status=503,
            )
        if not secrets.compare_digest(_bearer(request), expected):
            return JsonResponse({"error": "unauthorized"}, status=401)

        slug = _resolve_tenant_slug(request)
        if not slug:
            return JsonResponse(
                {"error": "tenant_required", "hint": "X-Tenant-ID veya body.tenant_slug"},
                status=400,
            )

        origin = (request.META.get("HTTP_ORIGIN") or "").strip().rstrip("/")
        allowed = origins_for_slug(slug)
        if origin and allowed:
            origin_ok = origin in {o.rstrip("/") for o in allowed}
            if not origin_ok:
                return JsonResponse(
                    {"error": "origin_not_allowed_for_tenant", "tenant_slug": slug},
                    status=403,
                )
        elif origin and not allowed:
            inferred = slug_for_origin(origin)
            if inferred and inferred.lower() != slug.lower():
                return JsonResponse(
                    {"error": "origin_slug_mismatch"},
                    status=403,
                )

        try:
            body = json.loads(request.body.decode("utf-8")) if request.body else {}
        except (ValueError, json.JSONDecodeError):
            return JsonResponse({"error": "invalid_json"}, status=400)

        if not isinstance(body, dict):
            return JsonResponse({"error": "body_must_be_object"}, status=400)

        event_type = str(body.get("event_type") or body.get("type") or "generic")[:120]
        payload = body.get("payload")
        if payload is None:
            payload = {k: v for k, v in body.items() if k not in ("event_type", "type", "tenant_slug", "tenant", "project")}

        rec = IntakeRecord.objects.create(
            tenant_slug=slug[:120],
            source_origin=origin[:512],
            event_type=event_type,
            payload=payload if isinstance(payload, dict) else {"value": payload},
        )
        return JsonResponse(
            {"ok": True, "id": rec.pk, "tenant_slug": rec.tenant_slug},
            status=201,
        )
