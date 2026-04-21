from django.contrib import admin

from apps.tenant.models import CrossTenantData, Tenant


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "domain", "data_type", "sync_to_tenant", "is_active")
    list_filter = ("is_active", "data_type")
    search_fields = ("name", "slug", "domain")
    raw_id_fields = ("sync_to_tenant",)


@admin.register(CrossTenantData)
class CrossTenantDataAdmin(admin.ModelAdmin):
    list_display = ("id", "source_tenant", "target_tenant", "user_external_id", "data_type", "synced_at", "is_processed")
    list_filter = ("data_type", "is_processed")
    search_fields = ("user_external_id",)
    raw_id_fields = ("source_tenant", "target_tenant")
    readonly_fields = ("synced_at",)
