from django.contrib import admin
from .models import Brand, ProductCategory, Product, ProductImage, ProductVariant, SizeChart


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ["name", "is_verified"]


@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "parent"]
    prepopulated_fields = {"slug": ("name",)}


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 0


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 0


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ["name", "brand", "price", "category"]
    inlines = [ProductImageInline, ProductVariantInline]


@admin.register(SizeChart)
class SizeChartAdmin(admin.ModelAdmin):
    list_display = ["brand", "category"]
