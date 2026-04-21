from django.urls import path

from . import views

app_name = "legal"

urlpatterns = [
    path("mesafeli-satis/", views.mesafeli_satis_view, name="mesafeli_satis"),
    path("iptal-iade/", views.iptal_iade_view, name="iptal_iade"),
    path("gizlilik/", views.gizlilik_view, name="gizlilik"),
    path("kvkk/", views.kvkk_view, name="kvkk"),
]
