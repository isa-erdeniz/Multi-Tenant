from django.contrib import admin
from .models import MakeupLook, MakeupProduct, MakeupSession


@admin.register(MakeupLook)
class MakeupLookAdmin(admin.ModelAdmin):
    list_display = ["name", "category", "is_premium"]


@admin.register(MakeupProduct)
class MakeupProductAdmin(admin.ModelAdmin):
    list_display = ["product_type", "color_hex", "brand"]


@admin.register(MakeupSession)
class MakeupSessionAdmin(admin.ModelAdmin):
    list_display = ["user", "created_at"]
