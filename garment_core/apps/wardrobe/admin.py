from django.contrib import admin

from .models import Garment, GarmentCategory, Outfit, WardrobeTag, WearLog


class _TenantScopedModelAdmin(admin.ModelAdmin):
    """Süper kullanıcı tüm kiracıları listeler; diğerleri yalnızca request tenant."""

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return self.model.all_objects.all()
        return qs


@admin.register(GarmentCategory)
class GarmentCategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "icon"]
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Garment)
class GarmentAdmin(_TenantScopedModelAdmin):
    list_display = ["name", "user", "category", "color", "season", "is_active", "created_at"]
    list_filter = ["category", "season", "is_active"]
    search_fields = ["name", "brand", "user__email"]
    list_editable = ["is_active"]
    readonly_fields = ["ai_analysis", "ai_analyzed_at", "created_at"]


@admin.register(Outfit)
class OutfitAdmin(_TenantScopedModelAdmin):
    list_display = ["name", "user", "occasion", "season"]


@admin.register(WardrobeTag)
class WardrobeTagAdmin(_TenantScopedModelAdmin):
    list_display = ["garment", "tag_name", "ai_generated"]


@admin.register(WearLog)
class WearLogAdmin(_TenantScopedModelAdmin):
    list_display = ["user", "date", "occasion"]
