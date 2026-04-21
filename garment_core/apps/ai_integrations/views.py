"""
DRF görünümleri — harici AI işlem API'si.
"""

from __future__ import annotations

import logging

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.ai_integrations.exceptions import (
    AIProviderError,
    ProviderRateLimitError,
    QuotaExceededError,
)
from apps.ai_integrations.models import AIProvider, AIProcessingTask
from apps.ai_integrations.permissions import HasTenantContext
from apps.ai_integrations.serializers import (
    AIProcessRequestSerializer,
    AIProcessingTaskSerializer,
    AIQuotaSerializer,
)
from apps.ai_integrations.services import (
    ProviderFactory,
    QuotaManager,
    enforce_provider_rate_limit,
    run_provider_cancel,
    run_provider_validate_and_estimate,
)
from apps.ai_integrations.tasks import process_ai_task
from apps.subscriptions.models import UserSubscription

logger = logging.getLogger(__name__)


class AIProcessView(APIView):
    """Harici AI işi oluşturur ve Celery kuyruğuna atar."""

    permission_classes = [IsAuthenticated, HasTenantContext]

    def post(self, request: Request) -> Response:
        ser = AIProcessRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        tenant = request.tenant

        provider_row = AIProvider.objects.filter(
            name=data["provider"],
            is_active=True,
        ).first()
        if provider_row is None:
            return Response(
                {"detail": str(_("Sağlayıcı yapılandırması bulunamadı."))},
                status=status.HTTP_400_BAD_REQUEST,
            )

        task = AIProcessingTask.objects.create(
            tenant=tenant,
            user=request.user,
            provider=provider_row,
            task_type=data["task_type"],
            status=AIProcessingTask.STATUS_QUEUED,
            input_data=data.get("input_data") or {},
        )

        try:
            _, estimated = run_provider_validate_and_estimate(task)
            enforce_provider_rate_limit(provider_row)
            with transaction.atomic():
                QuotaManager.check_quota(
                    tenant.pk,
                    request.user,
                    estimated,
                    lock_subscription=True,
                )
        except ProviderRateLimitError as exc:
            task.status = AIProcessingTask.STATUS_FAILED
            task.error_message = str(exc)[:2000]
            task.completed_at = timezone.now()
            task.save(
                update_fields=["status", "error_message", "completed_at", "updated_at"]
            )
            ra = int(getattr(exc, "retry_after", None) or 60)
            return Response(
                {"detail": str(exc), "retry_after": ra},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
                headers={"Retry-After": str(ra)},
            )
        except QuotaExceededError as exc:
            task.status = AIProcessingTask.STATUS_FAILED
            task.error_message = str(exc)[:2000]
            task.completed_at = timezone.now()
            task.save(
                update_fields=["status", "error_message", "completed_at", "updated_at"]
            )
            return Response(
                {
                    "detail": str(exc),
                    "required": exc.required,
                    "available": exc.available,
                },
                status=status.HTTP_402_PAYMENT_REQUIRED,
            )
        except AIProviderError as exc:
            task.status = AIProcessingTask.STATUS_FAILED
            task.error_message = str(exc)[:2000]
            task.completed_at = timezone.now()
            task.save(
                update_fields=["status", "error_message", "completed_at", "updated_at"]
            )
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        task.estimated_credits = estimated
        task.save(update_fields=["estimated_credits", "updated_at"])

        process_ai_task.delay(task.pk)
        return Response(
            {
                "task_id": task.pk,
                "status": task.status,
                "estimated_credits": estimated,
            },
            status=status.HTTP_202_ACCEPTED,
        )


class AITaskDetailView(APIView):
    """Tek bir AI iş kaydının durumunu döner."""

    permission_classes = [IsAuthenticated, HasTenantContext]

    def get(self, request: Request, pk: int) -> Response:
        task = get_object_or_404(
            AIProcessingTask.objects.filter(tenant=request.tenant),
            pk=pk,
        )
        return Response(AIProcessingTaskSerializer(task).data)


class AITaskCancelView(APIView):
    """İşlemi iptal eder; mümkünse uzak tarafta iptal ve kredi iadesi yapar."""

    permission_classes = [IsAuthenticated, HasTenantContext]

    def post(self, request: Request, pk: int) -> Response:
        task = get_object_or_404(
            AIProcessingTask.objects.filter(tenant=request.tenant),
            pk=pk,
        )
        if task.status in (
            AIProcessingTask.STATUS_COMPLETED,
            AIProcessingTask.STATUS_FAILED,
            AIProcessingTask.STATUS_CANCELLED,
        ):
            return Response(
                {"detail": str(_("Bu görev sonlandırılmış."))},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if task.external_task_id:
            try:
                impl = ProviderFactory.get_provider(task.provider.name)
                run_provider_cancel(impl, task.external_task_id)
            except AIProviderError as exc:
                logger.info("cancel remote skipped task_id=%s: %s", pk, exc)

        if task.credits_used:
            QuotaManager.refund_credits(task, reason="user_cancelled")
        task.credits_used = 0
        task.status = AIProcessingTask.STATUS_CANCELLED
        task.completed_at = timezone.now()
        task.save(
            update_fields=[
                "status",
                "completed_at",
                "credits_used",
                "updated_at",
            ]
        )
        return Response({"task_id": task.pk, "status": task.status})


class AIQuotaView(APIView):
    """Geçerli kullanıcı + tenant için harici AI kotası."""

    permission_classes = [IsAuthenticated, HasTenantContext]

    def get(self, request: Request) -> Response:
        sub = (
            UserSubscription.objects.filter(user=request.user, tenant=request.tenant)
            .select_related("plan")
            .first()
        )
        if sub is None or sub.plan is None:
            payload = {
                "plan_external_ai_enabled": False,
                "ai_credits_monthly": 0,
                "ai_credits_used": 0,
                "ai_credits_remaining": 0,
                "ai_credits_reset_date": None,
                "upcoming_reset_date": None,
            }
            return Response(AIQuotaSerializer(payload).data)

        QuotaManager._ensure_ai_period(sub)
        sub.refresh_from_db(fields=["ai_credits_used", "ai_credits_reset_date"])

        limit = int(sub.plan.ai_credits_monthly or 0)
        used = int(sub.ai_credits_used or 0)
        remaining = max(0, limit - used) if limit else 0
        if not sub.plan.external_ai_enabled:
            remaining = 0

        upcoming = QuotaManager.get_upcoming_reset_date(request.user, request.tenant.pk)
        payload = {
            "plan_external_ai_enabled": bool(sub.plan.external_ai_enabled),
            "ai_credits_monthly": limit,
            "ai_credits_used": used,
            "ai_credits_remaining": remaining,
            "ai_credits_reset_date": sub.ai_credits_reset_date,
            "upcoming_reset_date": upcoming,
        }
        return Response(AIQuotaSerializer(payload).data)
