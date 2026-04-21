from django.urls import path
from . import views

app_name = "beauty"

urlpatterns = [
    path("", views.beauty_index_view, name="index"),
    path("baslat/", views.beauty_start_view, name="start"),
    path("durum/<int:pk>/", views.beauty_status_view, name="status"),
]
