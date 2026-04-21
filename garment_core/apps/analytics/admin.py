from django.contrib import admin
from .models import UsageEvent


@admin.register(UsageEvent)
class UsageEventAdmin(admin.ModelAdmin):
    list_display = ["user", "event_type", "created_at"]
    list_filter = ["event_type"]
