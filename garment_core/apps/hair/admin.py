from django.contrib import admin
from .models import HairStyle, HairColor, HairSession


@admin.register(HairStyle)
class HairStyleAdmin(admin.ModelAdmin):
    list_display = ["name", "category", "gender", "is_premium"]


@admin.register(HairColor)
class HairColorAdmin(admin.ModelAdmin):
    list_display = ["name", "hex_code", "category"]


@admin.register(HairSession)
class HairSessionAdmin(admin.ModelAdmin):
    list_display = ["user", "created_at"]
