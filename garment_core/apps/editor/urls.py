from django.urls import path
from . import views

app_name = "editor"

urlpatterns = [
    path("", views.editor_view, name="index"),
]
