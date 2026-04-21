from django.contrib import admin

from .models import TryOnSession


@admin.register(TryOnSession)
class TryOnSessionAdmin(admin.ModelAdmin):
    list_display = ("user", "garment", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("user__email", "garment__name")
    raw_id_fields = ("user", "garment")

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return TryOnSession.all_objects.all()
        return qs
