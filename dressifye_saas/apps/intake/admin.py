from django.contrib import admin

from apps.intake.models import IntakeRecord


@admin.register(IntakeRecord)
class IntakeRecordAdmin(admin.ModelAdmin):
    list_display = ("tenant_slug", "event_type", "source_origin", "created_at")
    list_filter = ("tenant_slug", "event_type")
    search_fields = ("tenant_slug", "source_origin")
    readonly_fields = ("created_at",)
