from django.contrib import admin
from .models import LookPackage, LookRating


@admin.register(LookPackage)
class LookPackageAdmin(admin.ModelAdmin):
    list_display = ["name", "category", "is_premium"]


@admin.register(LookRating)
class LookRatingAdmin(admin.ModelAdmin):
    list_display = ["look", "user", "score"]
