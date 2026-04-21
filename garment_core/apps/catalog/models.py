"""
FAZ 13: Ürün Kataloğu & Marka Entegrasyonu
"""
from django.db import models

from apps.core.models import TimeStampedModel


class Brand(TimeStampedModel):
    """Marka."""
    name = models.CharField(max_length=200)
    logo = models.ImageField(upload_to="catalog/brands/", null=True, blank=True)
    description = models.TextField(blank=True)
    affiliate_config = models.JSONField(default=dict)
    is_verified = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Marka"
        verbose_name_plural = "Markalar"
        ordering = ["name"]


class ProductCategory(TimeStampedModel):
    """Kategori ağacı."""
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    parent = models.ForeignKey(
        "self", on_delete=models.CASCADE, null=True, blank=True, related_name="children"
    )

    class Meta:
        verbose_name = "Ürün Kategorisi"
        verbose_name_plural = "Ürün Kategorileri"
        ordering = ["name"]


class Product(TimeStampedModel):
    """Ürün."""
    brand = models.ForeignKey(
        Brand, on_delete=models.CASCADE, related_name="products"
    )
    name = models.CharField(max_length=200)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(blank=True)
    category = models.ForeignKey(
        ProductCategory, on_delete=models.SET_NULL, null=True, blank=True
    )
    sku = models.CharField(max_length=100, blank=True)

    class Meta:
        verbose_name = "Ürün"
        verbose_name_plural = "Ürünler"
        ordering = ["-created_at"]


class ProductImage(TimeStampedModel):
    """Ürün görseli."""
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="images"
    )
    image = models.ImageField(upload_to="catalog/products/%Y/%m/")
    is_primary = models.BooleanField(default=False)
    tryon_ready = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Ürün Görseli"
        verbose_name_plural = "Ürün Görselleri"


class ProductVariant(TimeStampedModel):
    """Beden/renk varyantı."""
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="variants"
    )
    size = models.CharField(max_length=20)
    color = models.CharField(max_length=50, blank=True)
    stock = models.PositiveIntegerField(default=0)
    price_override = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )

    class Meta:
        verbose_name = "Ürün Varyantı"
        verbose_name_plural = "Ürün Varyantları"


class SizeChart(TimeStampedModel):
    """Marka beden tablosu."""
    brand = models.ForeignKey(
        Brand, on_delete=models.CASCADE, related_name="size_charts"
    )
    category = models.ForeignKey(
        ProductCategory, on_delete=models.SET_NULL, null=True, blank=True
    )
    measurements_json = models.JSONField(default=dict)

    class Meta:
        verbose_name = "Beden Tablosu"
        verbose_name_plural = "Beden Tabloları"
