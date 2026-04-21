from django.urls import path
from . import views

app_name = "avatar"

urlpatterns = [
    path("", views.avatar_index_view, name="index"),
]
