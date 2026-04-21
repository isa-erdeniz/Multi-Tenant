from django.urls import path

from . import views

app_name = "tryon"

urlpatterns = [
    path("", views.tryon_view, name="index"),
    path("baslat/", views.tryon_start_view, name="start"),
    path("<int:pk>/durum/", views.tryon_status_view, name="status"),
    path("gecmis/", views.tryon_history_view, name="history"),
]
