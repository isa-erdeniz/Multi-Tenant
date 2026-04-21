from django.urls import path

from . import views

app_name = "wardrobe"

urlpatterns = [
    path("", views.wardrobe_view, name="index"),
    path("pin/", views.wardrobe_pin_grid_view, name="pin_grid"),
    path("liste/", views.wardrobe_list_view, name="list"),
    path("istatistikler/", views.wardrobe_stats_view, name="stats"),
    path("kombin-oner/", views.outfit_suggest_view, name="outfit_suggest"),
    path("kombin-giy/", views.outfit_wear_view, name="outfit_wear"),
    path("ekle/", views.garment_add_view, name="add"),
    path("<int:pk>/", views.garment_detail_view, name="detail"),
    path("<int:pk>/duzenle/", views.garment_edit_view, name="edit"),
    path("<int:pk>/sil/", views.garment_delete_view, name="delete"),
    path("<int:pk>/favori/", views.garment_favorite_toggle_view, name="favorite_toggle"),
    path("toplu-sil/", views.garment_bulk_delete_view, name="bulk_delete"),
]
