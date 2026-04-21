from django.urls import path
from . import views

app_name = "looks"

urlpatterns = [
    path("", views.looks_index_view, name="index"),
]
