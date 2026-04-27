from django.contrib import admin

from .models import Payment, WebhookEvent


@admin.register(WebhookEvent)
class WebhookEventAdmin(admin.ModelAdmin):
    list_display = ("reference_code", "event_type", "created_at")
    list_filter = ("event_type",)
    search_fields = ("reference_code", "event_type")
    readonly_fields = ("reference_code", "event_type", "created_at", "updated_at")


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "tenant",
        "plan",
        "amount",
        "period",
        "status",
        "created_at",
    )
    list_filter = ("status", "period", "plan")
    search_fields = ("user__email", "iyzico_payment_id", "tenant__slug")
    raw_id_fields = ("user", "tenant")
    readonly_fields = (
        "iyzico_token",
        "iyzico_payment_id",
        "iyzico_conversation_id",
        "created_at",
    )
