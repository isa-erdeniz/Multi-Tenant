"""Ürün kataloğu — marka ve ürün sayfaları."""
from django.shortcuts import get_object_or_404, render

from .models import Brand, Product


def brand_list_view(request):
    brands = Brand.objects.all().order_by("name")[:200]
    return render(request, "catalog/brand_list.html", {"brands": brands})


def brand_detail_view(request, pk):
    brand = get_object_or_404(Brand, pk=pk)
    products = (
        brand.products.select_related("category")
        .prefetch_related("images")
        .order_by("-created_at")[:48]
    )
    return render(
        request,
        "catalog/brand_detail.html",
        {"brand": brand, "products": products},
    )


def product_detail_view(request, pk):
    product = get_object_or_404(
        Product.objects.select_related("brand", "category"), pk=pk
    )
    images = list(product.images.all())
    variants = list(product.variants.all())
    return render(
        request,
        "catalog/product_detail.html",
        {
            "product": product,
            "images": images,
            "variants": variants,
        },
    )
