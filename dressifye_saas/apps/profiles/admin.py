from django.contrib import admin
from .models import UserProfile, BodyMeasurement, SizePreference, UserAvatar


@admin.register(BodyMeasurement)
class BodyMeasurementAdmin(admin.ModelAdmin):
    list_display = ["profile", "shoulder_width", "arm_length", "leg_length"]


@admin.register(SizePreference)
class SizePreferenceAdmin(admin.ModelAdmin):
    list_display = ["profile", "size_system", "top_size", "bottom_size"]


@admin.register(UserAvatar)
class UserAvatarAdmin(admin.ModelAdmin):
    list_display = ["profile", "body_type", "skin_tone"]


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "first_name", "body_shape", "skin_tone", "height", "weight", "onboarding_completed", "created_at")
    list_filter = ("body_shape", "skin_tone", "onboarding_completed")
    search_fields = ("user__email",)
    raw_id_fields = ("user",)
