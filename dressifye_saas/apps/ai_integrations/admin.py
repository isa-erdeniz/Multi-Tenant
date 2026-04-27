"""Django admin — AI sağlayıcı ve iş kayıtları (üretim gözlemi)."""

from __future__ import annotations

from django.contrib import admin, messages
from django.utils import timezone
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from apps.ai_integrations.models import AIProvider, AIProcessingTask, AIQuotaLog
from apps.ai_integrations.services import QuotaManager
from apps.ai_integrations.tasks import process_ai_task


class _TenantScopedModelAdmin(admin.ModelAdmin):
    """Süper kullanıcı tüm kiracıları görür."""

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return self.model.all_objects.all()
        return qs


@admin.register(AIProvider)
class AIProviderAdmin(admin.ModelAdmin):
    list_display = [
        "display_name_or_name",
        "name",
        "is_active",
        "rate_limit_per_minute",
        "cost_per_request",
        "supports_sync",
        "supports_async",
        "fallback_provider",
    ]
    list_filter = ["is_active", "name", "supports_sync", "supports_async"]
    search_fields = ["name", "display_name", "base_url"]
    raw_id_fields = ["fallback_provider"]
    fieldsets = (
        (
            None,
            {
                "fields": ("name", "display_name", "is_active"),
            },
        ),
        (
            _("API yapılandırması"),
            {
                "fields": ("base_url", "api_key_encrypted", "webhook_secret_encrypted", "fallback_provider"),
            },
        ),
        (
            _("Limitler ve yetenekler"),
            {
                "fields": (
                    "rate_limit_per_minute",
                    "cost_per_request",
                    "supports_sync",
                    "supports_async",
                    "config",
                ),
            },
        ),
    )

    @admin.display(description=_("Görünen ad"))
    def display_name_or_name(self, obj: AIProvider) -> str:
        return obj.display_name.strip() or obj.get_name_display()


@admin.register(AIProcessingTask)
class AIProcessingTaskAdmin(_TenantScopedModelAdmin):
    list_display = [
        "id",
        "colored_status",
        "tenant",
        "user",
        "provider",
        "task_type",
        "credits_used",
        "retry_count",
        "error_excerpt",
        "created_at",
    ]
    list_filter = ["status", "task_type", "provider", "tenant", "created_at"]
    search_fields = ["external_task_id", "user__email", "error_message"]
    readonly_fields = [
        "created_at",
        "updated_at",
        "started_at",
        "completed_at",
        "webhook_received_at",
        "processing_duration_display",
        "error_message_display",
        "output_data",
    ]
    raw_id_fields = ["tenant", "user", "provider"]
    actions = [
        "action_manual_refund",
        "action_force_retry",
        "action_cancel_tasks",
    ]
    fieldsets = (
        (
            _("Görev"),
            {"fields": ("tenant", "user", "provider", "task_type", "priority", "external_task_id")},
        ),
        (
            _("Durum"),
            {
                "fields": (
                    "status",
                    "retry_count",
                    "estimated_credits",
                    "credits_used",
                    "processing_duration_display",
                    "started_at",
                    "completed_at",
                    "webhook_received_at",
                ),
            },
        ),
        (
            _("Veri"),
            {"fields": ("input_data", "output_data")},
        ),
        (
            _("Hata"),
            {
                "fields": ("error_message_display",),
                "classes": ("wide",),
            },
        ),
        (
            _("Zaman damgaları"),
            {"fields": ("created_at", "updated_at")},
        ),
    )

    @admin.display(description=_("Durum"), ordering="status")
    def colored_status(self, obj: AIProcessingTask) -> str:
        palette = {
            AIProcessingTask.STATUS_QUEUED: "#6b7280",
            AIProcessingTask.STATUS_PROCESSING: "#2563eb",
            AIProcessingTask.STATUS_COMPLETED: "#059669",
            AIProcessingTask.STATUS_FAILED: "#dc2626",
            AIProcessingTask.STATUS_CANCELLED: "#d97706",
        }
        color = palette.get(obj.status, "#374151")
        label = obj.get_status_display()
        return format_html(
            '<span style="display:inline-block;padding:2px 8px;border-radius:4px;'
            'font-weight:600;background:#f3f4f6;color:{};">{}</span>',
            color,
            label,
        )

    @admin.display(description=_("Hata özeti"))
    def error_excerpt(self, obj: AIProcessingTask) -> str:
        if not obj.error_message:
            return "—"
        return (obj.error_message[:120] + "…") if len(obj.error_message) > 120 else obj.error_message

    @admin.display(description=_("İşlem süresi"))
    def processing_duration_display(self, obj: AIProcessingTask) -> str:
        d = obj.processing_duration
        return str(d) if d is not None else "—"

    @admin.display(description=_("Hata (tam metin)"))
    def error_message_display(self, obj: AIProcessingTask) -> str:
        if not obj.error_message:
            return "—"
        return format_html(
            '<pre style="white-space:pre-wrap;color:#dc3545;background:#fef2f2;padding:12px;'
            'border:1px solid #fecaca;border-radius:6px;max-height:320px;overflow:auto;">{}</pre>',
            obj.error_message,
        )

    @admin.action(description=_("Manuel kredi iadesi (başarısız / iptal)"))
    def action_manual_refund(self, request, queryset):
        n = 0
        for task in queryset:
            if task.credits_used and task.status in (
                AIProcessingTask.STATUS_FAILED,
                AIProcessingTask.STATUS_CANCELLED,
            ):
                QuotaManager.refund_credits(task, reason="admin_manual_refund")
                task.credits_used = 0
                task.save(update_fields=["credits_used", "updated_at"])
                n += 1
        self.message_user(
            request,
            _("%(count)s görev için iade işlendi.") % {"count": n},
            messages.SUCCESS,
        )

    @admin.action(description=_("Başarısız görevi zorla yeniden kuyruğa al"))
    def action_force_retry(self, request, queryset):
        n = 0
        for task in queryset.filter(status=AIProcessingTask.STATUS_FAILED):
            if task.credits_used:
                QuotaManager.refund_credits(task, reason="admin_force_retry")
            task.credits_used = 0
            task.status = AIProcessingTask.STATUS_QUEUED
            task.error_message = ""
            task.started_at = None
            task.completed_at = None
            task.external_task_id = ""
            task.retry_count = 0
            task.save(
                update_fields=[
                    "credits_used",
                    "status",
                    "error_message",
                    "started_at",
                    "completed_at",
                    "external_task_id",
                    "retry_count",
                    "updated_at",
                ]
            )
            process_ai_task.delay(task.pk)
            n += 1
        if n == 0:
            self.message_user(request, _("Yeniden kuyruğa alınacak başarısız görev yok."), messages.WARNING)
            return
        self.message_user(
            request,
            _("%(count)s görev zorla yeniden kuyruğa alındı.") % {"count": n},
            messages.SUCCESS,
        )

    @admin.action(description=_("Seçili görevleri iptal et ve mümkünse kredi iade et"))
    def action_cancel_tasks(self, request, queryset):
        n = 0
        for task in queryset:
            if task.status in (
                AIProcessingTask.STATUS_COMPLETED,
                AIProcessingTask.STATUS_CANCELLED,
                AIProcessingTask.STATUS_FAILED,
            ):
                continue
            if task.credits_used:
                QuotaManager.refund_credits(task, reason="admin_cancel_tasks")
            task.credits_used = 0
            task.status = AIProcessingTask.STATUS_CANCELLED
            task.completed_at = timezone.now()
            task.error_message = (task.error_message or "")[:2000] or "admin_cancelled"
            task.save(
                update_fields=[
                    "credits_used",
                    "status",
                    "completed_at",
                    "error_message",
                    "updated_at",
                ]
            )
            n += 1
        if n == 0:
            self.message_user(request, _("İptal edilecek uygun görev yok."), messages.WARNING)
            return
        self.message_user(
            request,
            _("%(count)s görev iptal edildi.") % {"count": n},
            messages.SUCCESS,
        )


@admin.register(AIQuotaLog)
class AIQuotaLogAdmin(_TenantScopedModelAdmin):
    list_display = [
        "id",
        "transaction_badge",
        "tenant",
        "user",
        "task",
        "credits_amount_colored",
        "balance_after",
        "created_at",
    ]
    list_filter = ["transaction_type", "tenant", "created_at"]
    search_fields = ["user__email", "description", "note"]
    readonly_fields = [f.name for f in AIQuotaLog._meta.fields]

    @admin.display(description=_("Miktar"))
    def credits_amount_colored(self, obj: AIQuotaLog) -> str:
        amt = int(obj.credits_amount or 0)
        if amt > 0:
            color = "#198754"
        elif amt < 0:
            color = "#dc3545"
        else:
            color = "#6c757d"
        return format_html(
            '<span style="font-weight:600;color:{};">{:+d}</span>',
            color,
            amt,
        )

    @admin.display(description=_("İşlem"))
    def transaction_badge(self, obj: AIQuotaLog) -> str:
        colors = {
            AIQuotaLog.TX_USAGE: "#dc2626",
            AIQuotaLog.TX_REFUND: "#059669",
            AIQuotaLog.TX_ADJUSTMENT: "#7c3aed",
            AIQuotaLog.TX_BONUS: "#0891b2",
        }
        c = colors.get(obj.transaction_type, "#374151")
        return format_html(
            '<span style="font-weight:600;color:{};">{}</span>',
            c,
            obj.get_transaction_type_display(),
        )

    def has_add_permission(self, request) -> bool:
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        return False
