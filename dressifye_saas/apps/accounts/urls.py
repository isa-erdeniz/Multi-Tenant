from django.urls import path

from . import views

app_name = "accounts"

# Giriş, kayıt, çıkış: django-allauth (hesap/login, hesap/signup, hesap/logout)
urlpatterns = [
    path("ayarlar/", views.profile_settings_view, name="settings"),
]
