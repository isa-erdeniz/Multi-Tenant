"""
DRF serializer'ları — harici AI API giriş/çıkışları.
"""

from __future__ import annotations

from typing import Any

from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from apps.ai_integrations.models import AIProcessingTask


class AIProcessRequestSerializer(serializers.Serializer):
    """POST /api/v1/ai/process/ gövdesi."""

    provider = serializers.CharField(max_length=32)
    task_type = serializers.ChoiceField(choices=AIProcessingTask.TASK_TYPE_CHOICES)
    input_data = serializers.JSONField(default=dict)

    def validate_provider(self, value: str) -> str:
        v = (value or "").strip().lower()
        allowed = {"wearview", "zmo", "style3d"}
        if v not in allowed:
            raise serializers.ValidationError(_("Geçersiz sağlayıcı."))
        return v


class AIProcessResponseSerializer(serializers.Serializer):
    """İş oluşturma yanıtı."""

    task_id = serializers.IntegerField()
    status = serializers.CharField()
    estimated_credits = serializers.IntegerField()
    retry_after = serializers.IntegerField(
        required=False,
        help_text=_("429 yanıtında tahmini bekleme süresi (saniye)."),
    )


class AIQuotaSerializer(serializers.Serializer):
    """GET /api/v1/ai/quota/ yanıtı."""

    plan_external_ai_enabled = serializers.BooleanField()
    ai_credits_monthly = serializers.IntegerField()
    ai_credits_used = serializers.IntegerField()
    ai_credits_remaining = serializers.IntegerField()
    ai_credits_reset_date = serializers.DateTimeField(allow_null=True)
    upcoming_reset_date = serializers.DateTimeField(allow_null=True, required=False)

    def to_representation(self, instance: dict[str, Any]) -> dict[str, Any]:
        data = super().to_representation(instance)
        if not isinstance(instance, dict):
            return data
        tz = timezone.get_current_timezone()
        for key in ("ai_credits_reset_date", "upcoming_reset_date"):
            raw = instance.get(key)
            if raw is not None:
                dt = raw
                if timezone.is_naive(dt):
                    dt = timezone.make_aware(dt, tz)
                elif settings.USE_TZ:
                    dt = timezone.localtime(dt, tz)
                data[key] = dt.isoformat()
            else:
                data[key] = None
        return data


class AIProcessingTaskSerializer(serializers.ModelSerializer):
    """Task detay API'si."""

    def to_representation(self, instance: AIProcessingTask) -> dict[str, Any]:
        data = super().to_representation(instance)
        tz = timezone.get_current_timezone()
        for key in (
            "created_at",
            "started_at",
            "completed_at",
            "webhook_received_at",
        ):
            if key in data and data[key] is not None:
                dt = getattr(instance, key, None)
                if dt is not None:
                    if timezone.is_naive(dt):
                        dt = timezone.make_aware(dt, tz)
                    elif settings.USE_TZ:
                        dt = timezone.localtime(dt, tz)
                    data[key] = dt.isoformat()
        return data

    class Meta:
        model = AIProcessingTask
        fields = (
            "id",
            "task_type",
            "status",
            "priority",
            "input_data",
            "output_data",
            "credits_used",
            "estimated_credits",
            "retry_count",
            "error_message",
            "external_task_id",
            "created_at",
            "started_at",
            "completed_at",
            "webhook_received_at",
        )
        read_only_fields = fields
