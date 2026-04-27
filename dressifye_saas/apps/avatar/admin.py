from django.contrib import admin
from .models import AvatarStyle, AvatarSession, BackgroundTemplate


@admin.register(AvatarStyle)
class AvatarStyleAdmin(admin.ModelAdmin):
    list_display = ["name", "category", "is_premium"]


@admin.register(AvatarSession)
class AvatarSessionAdmin(admin.ModelAdmin):
    list_display = ["user", "created_at"]


@admin.register(BackgroundTemplate)
class BackgroundTemplateAdmin(admin.ModelAdmin):
    list_display = ["name", "location_name"]
