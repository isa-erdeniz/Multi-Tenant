from django.urls import path

from . import views

app_name = "catalog"

urlpatterns = [
    path("", views.brand_list_view, name="brand_list"),
    path("marka/<int:pk>/", views.brand_detail_view, name="brand_detail"),
    path("urun/<int:pk>/", views.product_detail_view, name="product_detail"),
]
