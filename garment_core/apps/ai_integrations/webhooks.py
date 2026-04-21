"""
Harici AI sağlayıcılarından gelen webhook HTTP uçları (HMAC-SHA256 zorunlu, canlıda).
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
from typing import Any

from django.conf import settings
from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest, JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from apps.ai_integrations.models import AIProvider, AIProcessingTask
from apps.ai_integrations.services import QuotaManager

logger = logging.getLogger(__name__)


def _verify_hmac_hex(body: bytes, secret: str, signature_header: str | None) -> bool:
    """Ham gövde üzerinden HMAC-SHA256 (hex) doğrulaması."""
    if not secret or not signature_header:
        return False
    sig = signature_header.strip()
    if sig.startswith("sha256="):
        sig = sig.split("=", 1)[1]
    expected = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, sig)


class WebhookHandler:
    """Webhook imza çözümü ve (ileride) olay yönlendirme."""

    @classmethod
    def resolve_webhook_secret(cls, provider: AIProvider | str) -> str:
        """
        Önce veritabanı (``get_webhook_secret``), yoksa ortam değişkeni.

        Args:
            provider: ``AIProvider`` örneği veya ``name`` anahtarı (ör. ``wearview``).

        Returns:
            Boşlukları kırpılmış gizli anahtar; yoksa boş string.
        """
        if isinstance(provider, AIProvider):
            from_db = provider.get_webhook_secret()
            name = provider.name
        else:
            row = AIProvider.objects.filter(name=provider).first()
            from_db = row.get_webhook_secret() if row else ""
            name = str(provider)
        if from_db:
            return from_db
        env_map = {
            AIProvider.NAME_WEARVIEW: getattr(settings, "WEARVIEW_WEBHOOK_SECRET", ""),
            AIProvider.NAME_ZMO: getattr(settings, "ZMO_WEBHOOK_SECRET", ""),
            AIProvider.NAME_STYLE3D: getattr(settings, "STYLE3D_WEBHOOK_SECRET", ""),
        }
        return str(env_map.get(name, "") or "").strip()


def resolve_webhook_secret(provider_name: str) -> str:
    """Geriye dönük uyumluluk: :meth:`WebhookHandler.resolve_webhook_secret`."""
    return WebhookHandler.resolve_webhook_secret(provider_name)


def strict_webhook_signature_ok(
    provider_name: str,
    body: bytes,
    signature_header: str | None,
    *,
    enforce_strict: bool,
) -> bool:
    """
    WearView / Zmo için imza doğrulaması.

    Canlıda (enforce_strict=True) gizli anahtar tanımlıysa imza zorunludur.
    Gizli anahtar yoksa ve DEBUG + AI_WEBHOOK_ALLOW_UNSIGNED ise kabul (yalnız geliştirme).
    """
    secret = WebhookHandler.resolve_webhook_secret(provider_name)
    allow_unsigned = getattr(settings, "AI_WEBHOOK_ALLOW_UNSIGNED", False)

    if not secret:
        if settings.DEBUG and allow_unsigned:
            logger.warning(
                "AI webhook accepted without secret (dev only)",
                extra={"ai_event": "webhook_unsigned", "ai_provider": provider_name},
            )
            return True
        if enforce_strict:
            logger.error(
                "AI webhook missing secret",
                extra={"ai_event": "webhook_no_secret", "ai_provider": provider_name},
            )
            return False
        return bool(settings.DEBUG and allow_unsigned)

    if not signature_header:
        logger.warning(
            "AI webhook missing signature header",
            extra={"ai_event": "webhook_no_sig", "ai_provider": provider_name},
        )
        return False
    return _verify_hmac_hex(body, secret, signature_header)


def _parse_json(request: HttpRequest) -> dict[str, Any] | None:
    try:
        raw = request.body or b"{}"
        data = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _apply_task_update(
    *,
    provider_name: str,
    data: dict[str, Any],
    signature_ok: bool,
) -> JsonResponse:
    if not signature_ok:
        return JsonResponse({"detail": "invalid signature"}, status=403)

    ext_id = (
        data.get("external_task_id")
        or data.get("task_id")
        or data.get("job_id")
        or data.get("id")
    )
    if not ext_id:
        return JsonResponse({"detail": "missing task id"}, status=400)

    task = (
        AIProcessingTask.all_objects.select_related("provider")
        .filter(external_task_id=str(ext_id), provider__name=provider_name)
        .first()
    )
    if task is None:
        return JsonResponse({"detail": "unknown task"}, status=404)

    state = str(data.get("status") or data.get("state") or "").lower()
    out = task.output_data or {}
    if "result" in data:
        out["webhook"] = data.get("result")
    elif "output" in data:
        out["webhook"] = data.get("output")
    else:
        out["webhook"] = {k: v for k, v in data.items() if k != "status"}

    task.output_data = out
    task.webhook_received_at = timezone.now()

    if state in {"completed", "succeeded", "done"}:
        task.status = AIProcessingTask.STATUS_COMPLETED
        task.completed_at = timezone.now()
        task.error_message = ""
    elif state in {"failed", "error"}:
        if task.credits_used:
            QuotaManager.refund_credits(task, reason="webhook_failed")
            task.credits_used = 0
        task.status = AIProcessingTask.STATUS_FAILED
        task.error_message = str(data.get("message") or state)[:2000]
        task.completed_at = timezone.now()
    elif state in {"processing", "queued", "running"}:
        task.status = AIProcessingTask.STATUS_PROCESSING
    else:
        task.save(
            update_fields=["output_data", "webhook_received_at", "updated_at"],
        )
        return JsonResponse({"ok": True, "task_id": task.pk})

    task.save(
        update_fields=[
            "output_data",
            "webhook_received_at",
            "status",
            "error_message",
            "completed_at",
            "credits_used",
            "updated_at",
        ]
    )
    logger.info(
        "AI webhook updated",
        extra={
            "ai_event": "webhook_applied",
            "ai_task_id": task.pk,
            "ai_provider": provider_name,
            "ai_status": task.status,
        },
    )
    return JsonResponse({"ok": True, "task_id": task.pk})


@csrf_exempt
@require_POST
def wearview_webhook(request: HttpRequest) -> HttpResponse:
    """WearView webhook — imza zorunlu (canlı)."""
    body = request.body or b""
    sig = request.META.get("HTTP_X_WEARVIEW_SIGNATURE") or request.META.get(
        "HTTP_X_WEBHOOK_SIGNATURE"
    )
    ok = strict_webhook_signature_ok(
        AIProvider.NAME_WEARVIEW,
        body,
        sig,
        enforce_strict=True,
    )
    data = _parse_json(request)
    if data is None:
        return HttpResponseBadRequest("invalid json")
    return _apply_task_update(
        provider_name=AIProvider.NAME_WEARVIEW,
        data=data,
        signature_ok=ok,
    )


@csrf_exempt
@require_POST
def zmo_webhook(request: HttpRequest) -> HttpResponse:
    """Zmo.ai webhook — imza zorunlu (canlı)."""
    body = request.body or b""
    sig = request.META.get("HTTP_X_ZMO_SIGNATURE") or request.META.get("HTTP_X_WEBHOOK_SIGNATURE")
    ok = strict_webhook_signature_ok(
        AIProvider.NAME_ZMO,
        body,
        sig,
        enforce_strict=True,
    )
    data = _parse_json(request)
    if data is None:
        return HttpResponseBadRequest("invalid json")
    return _apply_task_update(
        provider_name=AIProvider.NAME_ZMO,
        data=data,
        signature_ok=ok,
    )


@csrf_exempt
@require_POST
def style3d_webhook(request: HttpRequest) -> HttpResponse:
    """Style3D webhook — gizli anahtar varsa aynı katı kurallar."""
    body = request.body or b""
    sig = request.META.get("HTTP_X_STYLE3D_SIGNATURE") or request.META.get(
        "HTTP_X_WEBHOOK_SIGNATURE"
    )
    secret = WebhookHandler.resolve_webhook_secret(AIProvider.NAME_STYLE3D)
    ok = strict_webhook_signature_ok(
        AIProvider.NAME_STYLE3D,
        body,
        sig,
        enforce_strict=bool(secret),
    )
    data = _parse_json(request)
    if data is None:
        return HttpResponseBadRequest("invalid json")
    return _apply_task_update(
        provider_name=AIProvider.NAME_STYLE3D,
        data=data,
        signature_ok=ok,
    )
