from django.contrib import admin
from .models import EditSession, EditPreset


@admin.register(EditSession)
class EditSessionAdmin(admin.ModelAdmin):
    list_display = ["user", "created_at"]


@admin.register(EditPreset)
class EditPresetAdmin(admin.ModelAdmin):
    list_display = ["name", "user", "is_public"]
