from django.urls import path
from . import views

app_name = "editor"

urlpatterns = [
    path("", views.editor_view, name="index"),
    path("yukle/", views.editor_upload_view, name="upload"),
    path("analiz/", views.editor_analyze_view, name="analyze"),
]
