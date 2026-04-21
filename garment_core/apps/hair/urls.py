from django.urls import path
from . import views

app_name = "hair"

urlpatterns = [
    path("", views.hair_index_view, name="index"),
    path("baslat/", views.hair_start_view, name="start"),
    path("durum/<int:pk>/", views.hair_status_view, name="status"),
]
