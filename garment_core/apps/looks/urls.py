from django.urls import path
from . import views

app_name = "looks"

urlpatterns = [
    path("", views.looks_index_view, name="index"),
    path("uygula/", views.looks_apply_view, name="apply"),
    path("durum/<int:pk>/", views.looks_status_view, name="status"),
]
