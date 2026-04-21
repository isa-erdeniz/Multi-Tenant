from django.urls import path

from . import views

app_name = "styling"

urlpatterns = [
    path("", views.styling_index_view, name="index"),
    path("yeni/", views.styling_new_view, name="new"),
    path("<int:pk>/", views.styling_result_view, name="result"),
    path("<int:pk>/durum/", views.styling_status_view, name="status"),
    path("<int:pk>/kaydet/", views.styling_save_view, name="save"),
]
