from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import DressifyeUser


@admin.register(DressifyeUser)
class DressifyeUserAdmin(BaseUserAdmin):
    list_display = ("email", "username", "is_staff", "is_trial_active", "trial_end_date", "date_joined")
    list_filter = ("is_staff", "is_trial_active", "is_active")
    search_fields = ("email", "username", "first_name", "last_name")
    ordering = ("-date_joined",)
    filter_horizontal = ()

    fieldsets = BaseUserAdmin.fieldsets + (
        ("Trial", {"fields": ("trial_end_date", "is_trial_active")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "username", "password1", "password2"),
        }),
    )
