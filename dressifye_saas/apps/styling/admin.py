from django.contrib import admin

from .models import StyleSession


@admin.register(StyleSession)
class StyleSessionAdmin(admin.ModelAdmin):
    list_display = [
        "user",
        "get_title",
        "status",
        "is_saved",
        "processing_time",
        "created_at",
    ]
    list_filter = ["status", "is_saved"]
    search_fields = ["user__email", "user_prompt"]
    readonly_fields = [
        "ai_response",
        "suggested_outfit",
        "processing_time",
        "created_at",
    ]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return StyleSession.all_objects.all()
        return qs
