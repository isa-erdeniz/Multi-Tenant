from django.contrib import admin

from .models import Tenant


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "slug",
        "domain",
        "owner_user",
        "is_active",
        "created_at",
    )
    list_filter = ("is_active",)
    search_fields = ("name", "slug", "domain", "owner_user__email")
    prepopulated_fields = {"slug": ("name",)}
    raw_id_fields = ("owner_user",)
    readonly_fields = ("created_at", "updated_at")
