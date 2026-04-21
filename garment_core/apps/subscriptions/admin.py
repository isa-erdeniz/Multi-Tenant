from django.contrib import admin

from .models import FeatureUsage, Plan, UserSubscription, UsageQuota


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "slug",
        "price_monthly",
        "price_yearly",
        "tryon_limit",
        "wardrobe_limit",
        "is_popular",
        "is_active",
        "order",
        "created_at",
    )
    list_filter = ("is_active", "is_popular")
    list_editable = ("order", "is_active")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (None, {"fields": ("name", "slug", "order", "is_active", "is_popular")}),
        ("Fiyat", {"fields": ("price_monthly", "price_yearly", "trial_days")}),
        (
            "Kullanım limitleri (0 = sınırsız)",
            {
                "fields": (
                    "tryon_limit",
                    "wardrobe_limit",
                    "look_limit",
                    "editor_limit",
                    "style_session_limit",
                )
            },
        ),
        (
            "Özellikler",
            {
                "fields": (
                    "has_ai_stylist",
                    "has_advanced_editor",
                    "has_social_sharing",
                    "has_priority_support",
                    "has_hq_export",
                )
            },
        ),
        ("Liste", {"fields": ("features",)}),
    )


@admin.register(UserSubscription)
class UserSubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "tenant",
        "plan",
        "status",
        "start_date",
        "end_date",
        "created_at",
    )
    list_filter = ("status", "plan")
    search_fields = ("user__email", "iyzico_subscription_ref", "tenant__slug")
    raw_id_fields = ("user",)
    autocomplete_fields = ("plan", "tenant")


@admin.register(UsageQuota)
class UsageQuotaAdmin(admin.ModelAdmin):
    list_display = ["user", "tryon_count", "wardrobe_count", "reset_date"]


@admin.register(FeatureUsage)
class FeatureUsageAdmin(admin.ModelAdmin):
    list_display = (
        "tenant",
        "user",
        "feature_type",
        "month",
        "count",
        "updated_at",
    )
    list_filter = ("feature_type", "month")
    search_fields = ("tenant__slug", "tenant__name", "user__email")
    raw_id_fields = ("tenant", "user")
    date_hierarchy = "month"
