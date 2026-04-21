"""
Dressifye inter-service REST API — kombin önerisi, gardırop analizi, geri bildirim.
"""
from __future__ import annotations

import json
import logging
import re
import time
from typing import Any

from asgiref.sync import async_to_sync
from django.conf import settings
from rest_framework import permissions, serializers, status
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from mehlr.models import OutfitRecommendation, OutfitRecommendationFeedback
from mehlr.integrations.webhooks import process_dressifye_webhook
from mehlr.services.ai_engine import _build_wardrobe_analysis_prompt, query_ai, query_dressifye_ai
from mehlr.services.context_manager import get_dressifye_context

logger = logging.getLogger("mehlr.api.dressifye")


class InterServiceAuth(permissions.BasePermission):
    """Dressifye → MEHLR: X-API-Key ve X-Service-Name doğrulaması."""

    def has_permission(self, request: Any, view: Any) -> bool:
        expected = (getattr(settings, "DRESSIFYE_API_KEY", "") or "").strip()
        if not expected or expected == "your-secret-key":
            logger.warning("DRESSIFYE_API_KEY yapılandırılmamış; Dressifye API reddedildi.")
            return False
        api_key = (request.headers.get("X-API-Key") or "").strip()
        service_name = (request.headers.get("X-Service-Name") or "").strip().lower()
        return api_key == expected and service_name == "dressifye"


class DressifyeAnonThrottle(AnonRateThrottle):
    scope = "dressifye"


class OutfitRequestSerializer(serializers.Serializer):
    user_id = serializers.CharField(required=True)
    query = serializers.CharField(required=True)
    occasion = serializers.CharField(required=False, allow_blank=True, default="")
    conversation_id = serializers.CharField(required=False, allow_blank=True, default="")
    hair_form = serializers.JSONField(required=False, default=dict)


class OutfitResponseSerializer(serializers.Serializer):
    recommendation_id = serializers.IntegerField(required=False, allow_null=True)
    outfit = serializers.DictField()
    style_notes = serializers.CharField()
    color_palette = serializers.ListField(child=serializers.CharField())
    confidence = serializers.FloatField()


class AnalyzeRequestSerializer(serializers.Serializer):
    user_id = serializers.CharField(required=True)


class FeedbackRequestSerializer(serializers.Serializer):
    recommendation_id = serializers.IntegerField(required=True, min_value=1)
    feedback = serializers.ChoiceField(choices=["liked", "disliked"])
    reason = serializers.CharField(required=False, allow_blank=True, default="")


def _extract_json(text: str) -> dict[str, Any] | None:
    if not text:
        return None
    m = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
    raw = m.group(1).strip() if m else text.strip()
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else None
    except (json.JSONDecodeError, TypeError, ValueError):
        return None


def _run_wardrobe_analysis(user_id: str) -> dict[str, Any]:
    """Senkron gardırop analizi (query_ai + get_dressifye_context)."""
    ctx = get_dressifye_context(user_id, include_profile=True)
    msg = _build_wardrobe_analysis_prompt(ctx, user_query=None)
    r = query_ai("dressifye", msg, conversation_history=None)
    raw_text = r.get("response") or ""
    parsed = _extract_json(raw_text)
    return {
        "analysis": parsed
        or {"raw": raw_text, "parse_error": True},
        "stats": ctx.get("stats", {}),
        "metadata": ctx.get("metadata", {}),
        "ai_error": r.get("error"),
    }


def _log_request(view_name: str, user_id: str | None, query: str | None, ms: float) -> None:
    logger.info(
        "dressifye.%s user_id=%s query_len=%s duration_ms=%.1f",
        view_name,
        user_id,
        len(query or ""),
        ms,
    )


class OutfitRecommendationView(APIView):
    authentication_classes: list[type] = []
    permission_classes = [InterServiceAuth]
    throttle_classes = [DressifyeAnonThrottle]

    def post(self, request: Any) -> Response:
        t0 = time.perf_counter()
        ser = OutfitRequestSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)
        data = ser.validated_data
        user_id = data["user_id"]
        q = data["query"]
        occasion = (data.get("occasion") or "").strip() or None
        conv = (data.get("conversation_id") or "").strip() or None
        hf = data.get("hair_form") or {}
        hair_form = hf if isinstance(hf, dict) and hf else None

        try:
            result = async_to_sync(query_dressifye_ai)(
                user_id=user_id,
                user_query=q,
                conversation_id=conv,
                occasion=occasion,
                include_wardrobe=True,
                hair_form=hair_form,
            )
        except Exception as e:
            logger.exception("query_dressifye_ai hatası: %s", e)
            _log_request("recommend", user_id, q, (time.perf_counter() - t0) * 1000)
            return Response(
                {"detail": "AI işlemi başarısız.", "error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        outfit = result.get("outfit_recommendation") or {}
        body = {
            "recommendation_id": result.get("recommendation_id") or outfit.get("recommendation_id"),
            "outfit": {
                "garment_ids": outfit.get("garment_ids", []),
                "description": outfit.get("description", ""),
                "occasion": outfit.get("occasion") or "",
            },
            "style_notes": outfit.get("style_notes", ""),
            "color_palette": outfit.get("color_palette", []),
            "confidence": float(result.get("confidence", 0.0)),
            "missing_items": result.get("missing_items", []),
            "raw_response": result.get("raw_response", ""),
        }
        _log_request("recommend", user_id, q, (time.perf_counter() - t0) * 1000)
        return Response(body, status=status.HTTP_200_OK)


class WardrobeAnalysisView(APIView):
    authentication_classes: list[type] = []
    permission_classes = [InterServiceAuth]
    throttle_classes = [DressifyeAnonThrottle]

    def post(self, request: Any) -> Response:
        t0 = time.perf_counter()
        ser = AnalyzeRequestSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)
        user_id = ser.validated_data["user_id"]
        try:
            out = _run_wardrobe_analysis(user_id)
        except Exception as e:
            logger.exception("wardrobe analysis: %s", e)
            _log_request("analyze", user_id, None, (time.perf_counter() - t0) * 1000)
            return Response(
                {"detail": "Analiz başarısız.", "error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        _log_request("analyze", user_id, None, (time.perf_counter() - t0) * 1000)
        return Response(out, status=status.HTTP_200_OK)


class OutfitFeedbackView(APIView):
    authentication_classes: list[type] = []
    permission_classes = [InterServiceAuth]
    throttle_classes = [DressifyeAnonThrottle]

    def post(self, request: Any) -> Response:
        t0 = time.perf_counter()
        ser = FeedbackRequestSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)
        rid = ser.validated_data["recommendation_id"]
        fb = ser.validated_data["feedback"]
        reason = ser.validated_data.get("reason") or ""

        try:
            rec = OutfitRecommendation.objects.get(pk=rid)
        except OutfitRecommendation.DoesNotExist:
            return Response(
                {"detail": "recommendation bulunamadı."},
                status=status.HTTP_404_NOT_FOUND,
            )

        OutfitRecommendationFeedback.objects.create(
            recommendation=rec,
            feedback=fb,
            reason=reason[:2000],
        )
        _log_request("feedback", str(rec.user.external_id), reason, (time.perf_counter() - t0) * 1000)
        return Response({"status": "ok", "recommendation_id": rid}, status=status.HTTP_201_CREATED)


class HealthCheckView(APIView):
    authentication_classes: list[type] = []
    permission_classes: list[type] = []

    def get(self, request: Any) -> Response:
        return Response({"status": "ok", "service": "mehlr"}, status=status.HTTP_200_OK)


class WebhookSerializer(serializers.Serializer):
    event = serializers.CharField(required=True)
    user_id = serializers.CharField(required=False, allow_blank=True, default="")
    external_id = serializers.CharField(required=False, allow_blank=True, default="")
    profile = serializers.JSONField(required=False, default=dict)
    data = serializers.JSONField(required=False, default=dict)
    payload = serializers.JSONField(required=False, default=dict)


class DressifyeWebhookView(APIView):
    """Dressifye sunucusundan webhook — arka planda senkron / cache invalidation."""

    authentication_classes: list[type] = []
    permission_classes = [InterServiceAuth]
    throttle_classes = [DressifyeAnonThrottle]

    def post(self, request: Any) -> Response:
        t0 = time.perf_counter()
        ser = WebhookSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)
        payload = dict(request.data)
        ok = process_dressifye_webhook(payload)
        _log_request(
            "webhook",
            str(payload.get("user_id") or ""),
            str(payload.get("event") or ""),
            (time.perf_counter() - t0) * 1000,
        )
        if not ok:
            return Response(
                {"detail": "Webhook işlenemedi (eksik alan veya hata)."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response({"status": "ok"}, status=status.HTTP_200_OK)
