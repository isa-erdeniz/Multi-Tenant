from django.urls import path
from . import views

app_name = "avatar"

urlpatterns = [
    path("", views.avatar_index_view, name="index"),
    path("baslat/", views.avatar_start_view, name="start"),
    path("durum/<int:pk>/", views.avatar_status_view, name="status"),
]
