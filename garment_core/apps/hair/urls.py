from django.urls import path
from . import views

app_name = "hair"

urlpatterns = [
    path("", views.hair_index_view, name="index"),
]
