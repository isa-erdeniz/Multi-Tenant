from django.urls import path
from . import views

app_name = "beauty"

urlpatterns = [
    path("", views.beauty_index_view, name="index"),
]
